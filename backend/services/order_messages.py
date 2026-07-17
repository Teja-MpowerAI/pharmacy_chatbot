"""
Patient-facing order status messages (confirmed / rejected) and the WebSocket
payload wrapper. Shared by both the admin PATCH endpoint (api/dashboard.py) and
the Supabase order-status webhook (api/webhooks/supabase.py) so the wording
lives in exactly one place.
"""
from __future__ import annotations

from typing import Any, Dict, Optional


def money(value) -> str:
    try:
        n = float(value)
    except (TypeError, ValueError):
        return f"₹{value}"
    return f"₹{int(n)}" if n == int(n) else f"₹{n:.2f}"


def confirmation_message(order: Dict[str, Any]) -> str:
    oid = str(order.get("id", ""))[:8]
    total = money(order.get("total_price"))
    if order.get("order_type") == "pickup":
        return (
            f"✅ *Your Order is Confirmed!*\n\nHi *{order.get('patient_name')}*, "
            f"your pickup order has been accepted.\n\n🧾 Order ID: {oid}\n"
            f"💰 Total: {total}\n🏪 Collect from: {order.get('address')}\n\n"
            "Please visit the store during working hours. Thank you for choosing "
            "1Health Pharmacy! 💊"
        )
    pay_line = (
        "💳 Payment: Online — Already Paid ✅"
        if order.get("payment_method") == "online"
        else f"💵 Cash on Delivery — please keep {total} ready."
    )
    return (
        f"✅ *Your Order is Confirmed!*\n\nHi *{order.get('patient_name')}*, your "
        f"delivery order has been accepted.\n\n🧾 Order ID: {oid}\n💰 Total: {total}\n"
        f"📍 Delivering to: {order.get('address')}\n{pay_line}\n\n"
        "⏰ Estimated delivery within 1 hour. Thank you for choosing 1Health "
        "Pharmacy! 💊"
    )


def rejection_message(order: Dict[str, Any]) -> str:
    oid = str(order.get("id", ""))[:8]
    refund = (
        f"💳 Since you paid online, {money(order.get('total_price'))} will be "
        "refunded within 2 hours."
        if order.get("payment_method") == "online"
        else "Please contact us or place a new order."
    )
    return (
        f"❌ *Order Rejected*\n\nHi *{order.get('patient_name')}*, unfortunately "
        f"your order could not be accepted.\n\n🧾 Order ID: {oid}\n{refund}\n\n"
        "Sorry for the inconvenience. — 1Health Pharmacy"
    )


def status_payload(order: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Build the WebSocket message for a status change, or None if the status is
    not one we notify on.
    """
    status = order.get("status")
    if status == "confirmed":
        text = confirmation_message(order)
    elif status == "rejected":
        text = rejection_message(order)
    else:
        return None
    return {"type": "message", "content": text, "quick_replies": [], "cards": []}
