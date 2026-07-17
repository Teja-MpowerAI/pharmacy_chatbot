"""
All Supabase (PostgREST) read/write operations for the pharmacy chatbot.

Design notes
------------
* This backend shares ONE database with the existing Telegram bot, so the data
  formats here must stay compatible with it. In particular `sessions.basket`
  and `orders.items` are stored as JSON *strings* (the n8n workflow uses
  JSON.stringify / JSON.parse). `loads_json` is tolerant: it also accepts a
  value that PostgREST already decoded into a list/dict (jsonb columns).
* The `supabase` Python client is synchronous. To avoid blocking the FastAPI
  event loop, every call is dispatched to a worker thread via
  `asyncio.to_thread`. All public methods are therefore `async`.
* The service-role key is used, which bypasses RLS. Keep it server-side only.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

from supabase import Client, create_client

from config import settings

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------
# JSON helpers (basket / items round-tripping)
# --------------------------------------------------------------------------
def dumps_json(value: Any) -> str:
    """Serialize a Python object to a compact JSON string for storage."""
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def loads_json(value: Any, default: Any = None) -> Any:
    """
    Tolerantly decode a value that may be a JSON string (text column) or an
    already-decoded list/dict (jsonb column) or None.
    """
    if value is None or value == "":
        return default if default is not None else []
    if isinstance(value, (list, dict)):
        return value
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        logger.warning("Could not decode JSON value: %r", value)
        return default if default is not None else []


class DatabaseService:
    """Thin async wrapper over the Supabase client with domain-specific ops."""

    def __init__(self) -> None:
        self.__client: Optional[Client] = None

    @property
    def _client(self) -> Client:
        """Lazily construct the Supabase client on first use.

        Deferring construction means the app can import and serve /health even
        before valid keys are in place; an invalid key surfaces on the first
        real query rather than crashing at import. NOTE: this client version
        requires a JWT-format key (service_role `eyJ...`), not an
        `sb_secret_...` style key.
        """
        if self.__client is None:
            self.__client = create_client(
                settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY
            )
        return self.__client

    # -- low-level dispatch -------------------------------------------------
    async def _run(self, fn, *args, **kwargs):
        return await asyncio.to_thread(fn, *args, **kwargs)

    # ======================================================================
    # SESSIONS
    # ======================================================================
    async def get_session(self, chat_id: str) -> Optional[Dict[str, Any]]:
        def _q():
            return (
                self._client.table("sessions")
                .select("*")
                .eq("chat_id", chat_id)
                .limit(1)
                .execute()
            )

        res = await self._run(_q)
        return res.data[0] if res.data else None

    async def create_session(
        self, chat_id: str, display_name: Optional[str] = None
    ) -> Dict[str, Any]:
        payload = {
            "chat_id": chat_id,
            "telegram_username": display_name,  # reused as web display name
            "current_step": "idle",
            "basket": "[]",
            "total_orders": 0,
            "total_spent": 0,
        }

        def _q():
            return self._client.table("sessions").insert(payload).execute()

        res = await self._run(_q)
        return res.data[0]

    async def get_or_create_session(
        self, chat_id: str, display_name: Optional[str] = None
    ) -> Dict[str, Any]:
        existing = await self.get_session(chat_id)
        if existing:
            return existing
        return await self.create_session(chat_id, display_name)

    async def update_session(
        self, chat_id: str, fields: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        def _q():
            return (
                self._client.table("sessions")
                .update(fields)
                .eq("chat_id", chat_id)
                .execute()
            )

        res = await self._run(_q)
        return res.data[0] if res.data else None

    async def reset_session(self, chat_id: str) -> Optional[Dict[str, Any]]:
        """
        Return a session to idle: clear the working step, basket and pincode.
        Deliberately does NOT touch chat_id (the n8n bot corrupted it here),
        nor the lifetime counters total_orders / total_spent.
        """
        return await self.update_session(
            chat_id,
            {"current_step": "idle", "basket": "[]", "pincode": None},
        )

    async def find_session_by_phone(
        self, phone: str
    ) -> Optional[Dict[str, Any]]:
        def _q():
            return (
                self._client.table("sessions")
                .select("*")
                .eq("phone_number", phone)
                .order("updated_at", desc=True)
                .limit(1)
                .execute()
            )

        try:
            res = await self._run(_q)
        except Exception:
            # `updated_at` may not exist; fall back to an unordered match.
            def _q2():
                return (
                    self._client.table("sessions")
                    .select("*")
                    .eq("phone_number", phone)
                    .limit(1)
                    .execute()
                )

            res = await self._run(_q2)
        return res.data[0] if res.data else None

    # ======================================================================
    # MEDICINES
    # ======================================================================
    async def get_medicines(
        self, in_stock_only: bool = False
    ) -> List[Dict[str, Any]]:
        def _q():
            query = self._client.table("medicines").select("*")
            if in_stock_only:
                query = query.gt("stock_quantity", 0)
            return query.execute()

        res = await self._run(_q)
        return res.data or []

    async def search_medicines(self, name: str) -> List[Dict[str, Any]]:
        """Case-insensitive substring search on medicine name (ilike %name%)."""
        term = (name or "").strip()
        if not term:
            return []

        def _q():
            return (
                self._client.table("medicines")
                .select("*")
                .ilike("name", f"%{term}%")
                .execute()
            )

        res = await self._run(_q)
        return res.data or []

    # ======================================================================
    # STORES / INVENTORY / ALIASES
    # ======================================================================
    async def get_stores(self) -> List[Dict[str, Any]]:
        def _q():
            return self._client.table("stores").select("*").order("id").execute()

        res = await self._run(_q)
        return res.data or []

    async def get_store_inventory(self) -> List[Dict[str, Any]]:
        def _q():
            return self._client.table("store_inventory").select("*").execute()

        res = await self._run(_q)
        return res.data or []

    async def get_aliases(self) -> List[Dict[str, Any]]:
        def _q():
            return self._client.table("medicine_aliases").select("*").execute()

        res = await self._run(_q)
        return res.data or []

    # ======================================================================
    # ORDERS
    # ======================================================================
    async def create_order(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Insert an order. `payload['items']` may be a list; it is serialized to
        a JSON string to match the shared-DB convention.
        """
        data = dict(payload)
        if "items" in data and not isinstance(data["items"], str):
            data["items"] = dumps_json(data["items"])

        def _q():
            return self._client.table("orders").insert(data).execute()

        res = await self._run(_q)
        return res.data[0]

    async def get_orders_by_chat(
        self, chat_id: str, limit: int = 3
    ) -> List[Dict[str, Any]]:
        def _q():
            return (
                self._client.table("orders")
                .select("*")
                .eq("chat_id", chat_id)
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )

        res = await self._run(_q)
        return res.data or []

    async def get_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        def _q():
            return (
                self._client.table("orders")
                .select("*")
                .eq("id", order_id)
                .limit(1)
                .execute()
            )

        res = await self._run(_q)
        return res.data[0] if res.data else None

    async def update_order_status(
        self, order_id: str, status: str
    ) -> Optional[Dict[str, Any]]:
        def _q():
            return (
                self._client.table("orders")
                .update({"status": status})
                .eq("id", order_id)
                .execute()
            )

        res = await self._run(_q)
        return res.data[0] if res.data else None

    async def list_orders(
        self, status: Optional[str] = None, limit: int = 50
    ) -> List[Dict[str, Any]]:
        def _q():
            query = self._client.table("orders").select("*")
            if status:
                query = query.eq("status", status)
            return query.order("created_at", desc=True).limit(limit).execute()

        res = await self._run(_q)
        return res.data or []

    async def get_latest_online_pending_order(
        self, chat_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Idempotency helper: returns the most recent pending online order for a
        session, so the Razorpay webhook and a typed 'PAID' cannot both insert
        a duplicate order for the same payment.
        """
        def _q():
            return (
                self._client.table("orders")
                .select("*")
                .eq("chat_id", chat_id)
                .eq("payment_method", "online")
                .eq("status", "pending")
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )

        res = await self._run(_q)
        return res.data[0] if res.data else None


# Singleton used across the app.
db = DatabaseService()
