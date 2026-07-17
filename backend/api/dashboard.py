"""
Admin dashboard REST API.

  GET   /api/orders?status=pending      list orders (optional status filter)
  GET   /api/orders/{id}                fetch one order
  PATCH /api/orders/{id}  {status}      confirm/reject -> notify the chat session

On confirm/reject we publish a patient-facing message to the order's session so
the patient's open WebSocket forwards it. NOTE: with the Supabase-webhook path
enabled (api/webhooks/supabase.py), status changes made directly in the DB also
notify the chat; this PATCH endpoint is the alternative "change via our API"
path and stays available for a built-in admin UI or manual use.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator

from services.database import db, loads_json
from services.order_messages import status_payload
from services.pubsub import publish_to_session

router = APIRouter(prefix="/api", tags=["admin"])


class OrderStatusUpdate(BaseModel):
    status: str

    @field_validator("status")
    @classmethod
    def _valid(cls, v: str) -> str:
        allowed = {"pending", "confirmed", "rejected", "delivered", "cancelled"}
        if v not in allowed:
            raise ValueError(f"status must be one of {sorted(allowed)}")
        return v


def _serialize(order: dict) -> dict:
    """Return an order with `items` decoded to a list for JSON responses."""
    out = dict(order)
    out["items"] = loads_json(order.get("items"), [])
    return out


@router.get("/orders")
async def list_orders(status: Optional[str] = None, limit: int = 50):
    orders = await db.list_orders(status=status, limit=limit)
    return {"orders": [_serialize(o) for o in orders]}


@router.get("/orders/{order_id}")
async def get_order(order_id: str):
    order = await db.get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return _serialize(order)


@router.patch("/orders/{order_id}")
async def update_order(order_id: str, body: OrderStatusUpdate):
    order = await db.get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    updated = await db.update_order_status(order_id, body.status)
    payload = status_payload(updated or order)
    if payload:
        await publish_to_session(str(order.get("chat_id")), payload)

    return {"order": _serialize(updated or order), "notified": bool(payload)}
