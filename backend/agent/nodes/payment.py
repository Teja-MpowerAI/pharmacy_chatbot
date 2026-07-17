"""
Payment flow: COD order creation, Razorpay online payment link, and the
idempotent online-order creation shared by typed "PAID" and the webhook.

Idempotency
-----------
`create_online_order_from_session` first checks for an existing pending online
order for the session. Both the typed-"PAID" handler and
api/webhooks/razorpay.py call it, so a genuine payment produces exactly one
order even if the webhook fires and the user also types PAID.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Tuple

from config import settings
from agent.state import MAIN_MENU_REPLIES, PharmacyState
from agent.nodes.delivery import _compute_totals
from agent.nodes.pickup import money
from services.database import db, loads_json
from services.razorpay import RazorpayNotConfigured, create_payment_link

logger = logging.getLogger(__name__)


async def _create_delivery_order(
    *,
    chat_id: str,
    patient_name,
    phone_number,
    address,
    pincode,
    items,
    total_price: float,
    payment_method: str,
    prescription_image_url,
) -> Dict[str, Any]:
    return await db.create_order(
        {
            "chat_id": chat_id,
            "patient_name": patient_name,
            "phone_number": phone_number,
            "address": address,
            "pincode": pincode,
            "items": items,
            "total_price": total_price,
            "status": "pending",
            "order_type": "delivery",
            "payment_method": payment_method,
            "prescription_image_url": prescription_image_url,
        }
    )


# --------------------------------------------------------------------------
# COD  (button: cod)
# --------------------------------------------------------------------------
async def handle_pay_cod(state: PharmacyState) -> PharmacyState:
    totals = await _compute_totals(state.get("basket", []))
    order = await _create_delivery_order(
        chat_id=state["chat_id"],
        patient_name=state.get("patient_name"),
        phone_number=state.get("phone_number"),
        address=state.get("address"),
        pincode=state.get("pincode"),
        items=totals["enriched"],
        total_price=totals["cod_total"],
        payment_method="cod",
        prescription_image_url=state.get("prescription_image_url"),
    )

    state["basket"] = []
    state["current_step"] = "idle"
    state["order_type"] = None
    state["pincode"] = None

    state["response_type"] = "message"
    state["reply_message"] = (
        f"🎉 *Order Received!*\n\nHi *{state.get('patient_name')}*, your delivery "
        f"order is placed.\n\n💵 Payment: Cash on Delivery\n"
        f"🚚 Delivery charge: {money(settings.DELIVERY_CHARGE_COD)}\n"
        f"💰 *Total to pay on delivery: {money(totals['cod_total'])}*\n"
        f"📍 Deliver to: {state.get('address')} - {state.get('pincode')}\n"
        f"🧾 Order ID: {str(order.get('id', ''))[:8]}\n\n"
        "⏳ Our pharmacy team is reviewing your order. You'll get a confirmation "
        "message once it's accepted.\n\nThank you for choosing 1Health Pharmacy! 💊"
    )
    return state


# --------------------------------------------------------------------------
# Online  (button: online) -> create Razorpay link
# --------------------------------------------------------------------------
async def handle_pay_online(state: PharmacyState) -> PharmacyState:
    totals = await _compute_totals(state.get("basket", []))
    amount = totals["online_total"]
    state["response_type"] = "message"

    try:
        link = await create_payment_link(
            amount_inr=amount,
            name=state.get("patient_name") or "Customer",
            contact=state.get("phone_number") or "",
            chat_id=state["chat_id"],
        )
    except RazorpayNotConfigured:
        state["reply_message"] = (
            "Online payment isn't configured for this demo. Please choose "
            "*Cash on Delivery* instead."
        )
        state["quick_replies"] = [{"label": "💵 Cash on Delivery", "value": "cod"}]
        return state
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to create Razorpay link: %s", exc)
        state["reply_message"] = (
            "Sorry, we couldn't create a payment link right now. Please try "
            "*Cash on Delivery*."
        )
        state["quick_replies"] = [{"label": "💵 Cash on Delivery", "value": "cod"}]
        return state

    # Keep the basket/session intact; the webhook (or typed PAID) finalises it.
    state["current_step"] = "online_payment_pending"
    state["payment_method"] = "online"
    state["response_type"] = "payment"
    state["payment_link"] = link["short_url"]
    state["reply_message"] = (
        f"💳 *Complete Your Payment*\n\n"
        f"Amount: *{money(amount)}* (incl. {money(settings.DELIVERY_CHARGE_ONLINE)} "
        "delivery)\n\nTap the button to pay securely via UPI, Card, Netbanking or "
        "Wallet. Your order is confirmed automatically once payment succeeds.\n\n"
        "Already paid? Reply *PAID*."
    )
    return state


# --------------------------------------------------------------------------
# Shared idempotent online-order creation (typed PAID + webhook)
# --------------------------------------------------------------------------
async def create_online_order_from_session(
    session: Dict[str, Any], amount_paid: float
) -> Tuple[Dict[str, Any], bool]:
    """
    Create the online delivery order for a session if one doesn't already exist.
    Returns (order, created) where `created` is False if it was already there.
    """
    chat_id = session.get("chat_id")
    existing = await db.get_latest_online_pending_order(chat_id)
    if existing:
        return existing, False

    basket = loads_json(session.get("basket"), [])
    order = await _create_delivery_order(
        chat_id=chat_id,
        patient_name=session.get("patient_name"),
        phone_number=session.get("phone_number"),
        address=session.get("address"),
        pincode=session.get("pincode"),
        items=basket,
        total_price=amount_paid,
        payment_method="online",
        prescription_image_url=session.get("prescription_image_url"),
    )
    return order, True


# --------------------------------------------------------------------------
# Typed "PAID" while online_payment_pending
# --------------------------------------------------------------------------
async def handle_online_payment_confirm(state: PharmacyState) -> PharmacyState:
    totals = await _compute_totals(state.get("basket", []))
    session_like = {
        "chat_id": state["chat_id"],
        "patient_name": state.get("patient_name"),
        "phone_number": state.get("phone_number"),
        "address": state.get("address"),
        "pincode": state.get("pincode"),
        "basket": state.get("basket", []),
        "prescription_image_url": state.get("prescription_image_url"),
    }
    order, created = await create_online_order_from_session(
        session_like, totals["online_total"]
    )

    state["basket"] = []
    state["current_step"] = "idle"
    state["order_type"] = None
    state["pincode"] = None
    state["payment_method"] = None

    state["response_type"] = "message"
    lead = (
        "✅ *Payment Confirmed!*" if created else "✅ *Payment already received!*"
    )
    state["reply_message"] = (
        f"{lead}\n\nHi *{state.get('patient_name')}*, your order is placed.\n\n"
        f"📱 Payment: Online\n🧾 Order ID: {str(order.get('id', ''))[:8]}\n\n"
        "⏳ Our pharmacy team is reviewing your order. You'll get a confirmation "
        "message once it's accepted.\n\nThank you for choosing 1Health Pharmacy! 💊"
    )
    state["quick_replies"] = MAIN_MENU_REPLIES
    return state
