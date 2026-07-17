"""
Razorpay webhook.

  POST /api/webhooks/razorpay

Verifies the X-Razorpay-Signature against the raw body, then on
`payment_link.paid` creates the order (idempotently — see
create_online_order_from_session) and pushes a confirmation into the patient's
open chat via Redis. Failure/expiry events push a friendly notice.

For a local demo, expose this endpoint with ngrok and register the https URL +
webhook secret in the Razorpay dashboard.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Header, Request, Response

from agent.nodes.payment import create_online_order_from_session
from agent.state import MAIN_MENU_REPLIES
from services.database import db
from services.pubsub import publish_to_session
from services.razorpay import verify_webhook_signature

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


def _dig(d: Dict[str, Any], *path, default=None):
    cur: Any = d
    for key in path:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(key)
    return cur if cur is not None else default


async def _resolve_session(
    chat_id: Optional[str], contact: Optional[str]
) -> Optional[Dict[str, Any]]:
    if chat_id:
        session = await db.get_session(str(chat_id))
        if session:
            return session
    if contact:
        phone = str(contact).replace("+91", "").strip()
        return await db.find_session_by_phone(phone)
    return None


@router.post("/razorpay")
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: str = Header(default=""),
):
    body = await request.body()

    if not verify_webhook_signature(body, x_razorpay_signature):
        logger.warning("Rejected Razorpay webhook: bad signature")
        return Response(status_code=400, content="invalid signature")

    payload = await request.json()
    event = payload.get("event", "")

    chat_id = _dig(payload, "payload", "payment_link", "entity", "notes", "chat_id")
    contact = _dig(
        payload, "payload", "payment_link", "entity", "customer", "contact"
    ) or _dig(payload, "payload", "payment", "entity", "contact")

    # ---- Payment succeeded ------------------------------------------------
    if event == "payment_link.paid":
        amount_paise = _dig(
            payload, "payload", "payment_link", "entity", "amount", default=0
        )
        amount = float(amount_paise) / 100.0

        session = await _resolve_session(chat_id, contact)
        if not session:
            logger.warning("payment_link.paid: no session for chat_id=%s contact=%s",
                           chat_id, contact)
            return {"ok": True, "matched": False}

        order, created = await create_online_order_from_session(session, amount)
        await db.reset_session(str(session["chat_id"]))

        await publish_to_session(
            str(session["chat_id"]),
            {
                "type": "message",
                "content": (
                    "✅ *Payment Successful!*\n\nWe've received your payment. "
                    f"🧾 Order ID: {str(order.get('id', ''))[:8]}\n\n"
                    "Your order is now being reviewed by our pharmacy team — you'll "
                    "get a confirmation shortly. Thank you for choosing 1Health "
                    "Pharmacy! 💊"
                ),
                "quick_replies": MAIN_MENU_REPLIES,
                "cards": [],
            },
        )
        return {"ok": True, "matched": True, "created": created}

    # ---- Payment link expired / payment failed ----------------------------
    if event in ("payment_link.expired", "payment.failed"):
        session = await _resolve_session(chat_id, contact)
        if session:
            await publish_to_session(
                str(session["chat_id"]),
                {
                    "type": "message",
                    "content": (
                        "⚠️ *Payment not completed.*\n\nYour payment link expired or "
                        "the payment failed. Please try again or choose Cash on "
                        "Delivery."
                    ),
                    "quick_replies": MAIN_MENU_REPLIES,
                    "cards": [],
                },
            )
        return {"ok": True, "event": event}

    # Any other event — acknowledge so Razorpay doesn't retry.
    return {"ok": True, "ignored": event}
