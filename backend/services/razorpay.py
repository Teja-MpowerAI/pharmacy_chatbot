"""
Razorpay integration: payment-link creation and webhook signature verification.

The payment link carries the session's `chat_id` in `notes`, so the webhook can
match the payment back to the exact session (more reliable than matching by
phone number, which the n8n bot did).
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any, Dict

from config import settings

logger = logging.getLogger(__name__)

try:
    import razorpay  # type: ignore
except ImportError as _exc:  # pragma: no cover
    logger.warning("razorpay SDK import failed (%s) — online payment disabled", _exc)
    razorpay = None

_client = None
if razorpay is not None and settings.razorpay_enabled:
    _client = razorpay.Client(
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
    )


class RazorpayNotConfigured(RuntimeError):
    pass


async def create_payment_link(
    amount_inr: float,
    name: str,
    contact: str,
    chat_id: str,
    description: str = "1Health Pharmacy Order",
) -> Dict[str, Any]:
    """Create a Razorpay payment link and return {id, short_url, amount}."""
    if _client is None:
        raise RazorpayNotConfigured("Razorpay keys are not configured.")

    payload = {
        "amount": int(round(float(amount_inr) * 100)),  # paise
        "currency": "INR",
        "description": description,
        "customer": {"name": name or "Customer", "contact": contact or ""},
        "notify": {"sms": False, "email": False},
        "reminder_enable": False,
        "notes": {"chat_id": str(chat_id)},
        "reference_id": f"{chat_id}-{uuid.uuid4().hex[:8]}",
    }

    def _create():
        return _client.payment_link.create(payload)

    res = await asyncio.to_thread(_create)
    return {
        "id": res.get("id"),
        "short_url": res.get("short_url"),
        "amount": res.get("amount"),
    }


def verify_webhook_signature(body: bytes, signature: str) -> bool:
    """
    Verify the X-Razorpay-Signature header against the raw request body using the
    configured webhook secret. Returns False on any mismatch/error.
    """
    if _client is None or not settings.RAZORPAY_WEBHOOK_SECRET:
        logger.warning("Cannot verify webhook: Razorpay client/secret missing.")
        return False
    try:
        _client.utility.verify_webhook_signature(
            body.decode("utf-8"),
            signature,
            settings.RAZORPAY_WEBHOOK_SECRET,
        )
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning("Razorpay webhook signature verification failed: %s", exc)
        return False
