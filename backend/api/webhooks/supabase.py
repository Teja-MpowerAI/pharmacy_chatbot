"""
Supabase order-status Database Webhook.

  POST /api/webhooks/supabase/order-status

Mirrors the n8n "Pharmacy Order Notifications" flow, but for the web chat:
whenever an `orders` row's status changes (via the admin page, a direct DB edit,
or anything else), Supabase fires this webhook and we push the confirmation /
rejection message into the customer's live chat.

Configure in Supabase: Database -> Webhooks -> Create a new hook on table
`orders`, event UPDATE, method POST, URL
`<PUBLIC_BASE_URL>/api/webhooks/supabase/order-status`. Add a custom header
`x-webhook-secret: <SUPABASE_WEBHOOK_SECRET>` if you set that env var. For local
testing the backend must be publicly reachable (e.g. ngrok).

Supabase sends:
  {
    "type": "UPDATE", "table": "orders", "schema": "public",
    "record":     { ...new row... },
    "old_record": { ...previous row... }
  }
"""
from __future__ import annotations

import logging
from typing import Any, Dict

from fastapi import APIRouter, Header, Request, Response

from config import settings
from services.order_messages import status_payload
from services.pubsub import publish_to_session

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/webhooks/supabase", tags=["webhooks"])

_NOTIFY_STATUSES = {"confirmed", "rejected"}


@router.post("/order-status")
async def order_status(
    request: Request,
    x_webhook_secret: str = Header(default=""),
):
    # Optional shared-secret check.
    if settings.SUPABASE_WEBHOOK_SECRET:
        if x_webhook_secret != settings.SUPABASE_WEBHOOK_SECRET:
            logger.warning("Rejected Supabase webhook: bad secret header")
            return Response(status_code=401, content="invalid secret")

    try:
        payload: Dict[str, Any] = await request.json()
    except Exception:  # noqa: BLE001
        return Response(status_code=400, content="invalid json")

    if payload.get("table") != "orders":
        return {"ok": True, "ignored": "not orders table"}

    record = payload.get("record") or {}
    old = payload.get("old_record") or {}
    new_status = record.get("status")
    old_status = old.get("status")

    # Only notify when the status actually changed INTO a notify-able state, so a
    # webhook fired by some other column update doesn't re-send the message.
    if new_status not in _NOTIFY_STATUSES or new_status == old_status:
        return {"ok": True, "notified": False, "status": new_status}

    chat_id = record.get("chat_id")
    ws_payload = status_payload(record)
    if not chat_id or not ws_payload:
        return {"ok": True, "notified": False}

    await publish_to_session(str(chat_id), ws_payload)
    logger.info("Order %s -> %s, notified session %s",
                str(record.get("id"))[:8], new_status, chat_id)
    return {"ok": True, "notified": True, "status": new_status}
