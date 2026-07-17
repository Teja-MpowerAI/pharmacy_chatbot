"""
Delivery flow.

Steps: select_delivery -> delivery_collecting_name -> delivery_collecting_phone
-> delivery_collecting_address -> delivery_collecting_pincode ->
delivery_confirming (choose payment) -> payment node.

Business rules:
  * Pincode must appear in some store's `serviceable_pincodes` (comma-separated).
    Each pincode is TRIMMED before comparison (n8n forgot to, so
    "500081, 500084" never matched "500084").
  * Minimum order value (default ₹1000) applies to PRESCRIPTION orders only,
    detected via a price-less basket (`has_preset_prices` is False).
  * COD adds ₹40, Online adds ₹20 (the online charge is framed as a discount).
Totals are recomputed here for display and again in the payment node at
selection time — nothing transient is persisted.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from config import settings
from agent.state import MAIN_MENU_REPLIES, PAYMENT_REPLIES, PharmacyState
from agent.nodes.pickup import money
from services.database import db
from services.matching import enrich_basket_prices, has_preset_prices


def _pincode_serviced(pincode: str, stores: List[Dict[str, Any]]) -> Optional[str]:
    """Return the name of the first store that services `pincode`, else None."""
    for store in stores:
        raw = store.get("serviceable_pincodes") or ""
        serviced = [p.strip() for p in str(raw).split(",") if p.strip()]
        if pincode in serviced:
            return store.get("name")
    return None


async def _compute_totals(basket: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Enrich basket prices and compute subtotal + COD/online totals."""
    medicines = await db.get_medicines()
    aliases = await db.get_aliases()
    preset = has_preset_prices(basket)
    enriched, subtotal = enrich_basket_prices(basket, medicines, aliases)
    return {
        "enriched": enriched,
        "subtotal": subtotal,
        "cod_total": subtotal + settings.DELIVERY_CHARGE_COD,
        "online_total": subtotal + settings.DELIVERY_CHARGE_ONLINE,
        "is_prescription_order": not preset,
    }


# --------------------------------------------------------------------------
# select_delivery  (button)
# --------------------------------------------------------------------------
async def handle_select_delivery(state: PharmacyState) -> PharmacyState:
    if not state.get("basket"):
        state["response_type"] = "message"
        state["reply_message"] = (
            "Your basket is empty. Add a medicine or upload a prescription first. 🛒"
        )
        state["quick_replies"] = MAIN_MENU_REPLIES
        return state

    state["order_type"] = "delivery"
    state["current_step"] = "delivery_collecting_name"
    state["response_type"] = "message"
    state["reply_message"] = (
        "Great, *Home Delivery* selected! 🚚\n\nPlease tell me your *full name*."
    )
    return state


# --------------------------------------------------------------------------
# delivery_collecting_name
# --------------------------------------------------------------------------
async def handle_delivery_name(state: PharmacyState) -> PharmacyState:
    name = (state.get("extracted_name") or state.get("input_text") or "").strip()
    state["patient_name"] = name
    state["current_step"] = "delivery_collecting_phone"
    state["response_type"] = "message"
    state["reply_message"] = (
        f"Thank you *{name}*! 🙏\n\nWhat's your *10-digit phone number* for "
        "delivery confirmation?"
    )
    return state


# --------------------------------------------------------------------------
# delivery_collecting_phone
# --------------------------------------------------------------------------
async def handle_delivery_phone(state: PharmacyState) -> PharmacyState:
    phone = state.get("extracted_phone")
    if not phone or len(phone) < 10:
        state["response_type"] = "message"
        state["reply_message"] = "Please send a valid 10-digit phone number. 📱"
        return state
    state["phone_number"] = phone
    state["current_step"] = "delivery_collecting_address"
    state["response_type"] = "message"
    state["reply_message"] = (
        "Got it! Now please send your *delivery address* — street, area and city."
    )
    return state


# --------------------------------------------------------------------------
# delivery_collecting_address
# --------------------------------------------------------------------------
async def handle_delivery_address(state: PharmacyState) -> PharmacyState:
    address = (state.get("extracted_address") or state.get("input_text") or "").strip()
    state["address"] = address
    state["current_step"] = "delivery_collecting_pincode"
    state["response_type"] = "message"
    state["reply_message"] = (
        "Almost done! Please send your *6-digit pincode* so we can assign the "
        "nearest store. 📍"
    )
    return state


# --------------------------------------------------------------------------
# delivery_collecting_pincode -> range check, min-order check, show payment
# --------------------------------------------------------------------------
async def handle_delivery_pincode(state: PharmacyState) -> PharmacyState:
    pincode = state.get("extracted_pincode")
    state["response_type"] = "message"

    if not pincode or len(pincode) != 6:
        state["reply_message"] = "Please send a valid 6-digit pincode. 📍"
        return state

    stores = await db.get_stores()
    serviced_by = _pincode_serviced(pincode, stores)
    if not serviced_by:
        # Out of range -> reject and reset.
        state["reply_message"] = (
            f"😔 *Delivery Not Available*\n\nSorry, we don't currently deliver to "
            f"pincode *{pincode}*.\n\nYou can still choose *Pickup* from one of our "
            "stores. Type *catalog* to start again."
        )
        state["basket"] = []
        state["current_step"] = "idle"
        state["pincode"] = None
        state["quick_replies"] = MAIN_MENU_REPLIES
        return state

    state["pincode"] = pincode

    totals = await _compute_totals(state.get("basket", []))

    # Minimum order value — prescription orders only.
    if totals["is_prescription_order"] and totals["subtotal"] < settings.DELIVERY_MIN_ORDER:
        state["reply_message"] = (
            f"❌ *Minimum Order Not Met*\n\nYour order total is "
            f"{money(totals['subtotal'])}, but the minimum for prescription "
            f"delivery is {money(settings.DELIVERY_MIN_ORDER)}.\n\n"
            "Please add more medicines, or choose *Pickup* (no minimum). "
            "Type *catalog* to browse."
        )
        state["basket"] = []
        state["current_step"] = "idle"
        state["pincode"] = None
        state["quick_replies"] = MAIN_MENU_REPLIES
        return state

    item_lines = "\n".join(
        f"• {i['name']}"
        + (f" {i['dosage']}" if i.get("dosage") else "")
        + f" ×{i['quantity']} = {money(i['price'] * i['quantity'])}"
        for i in totals["enriched"]
    )

    state["current_step"] = "delivery_confirming"
    state["response_type"] = "message"
    state["reply_message"] = (
        f"🚚 *Delivery Order Summary*\n\n{item_lines}\n\n"
        f"*Subtotal: {money(totals['subtotal'])}*\n\n"
        f"💵 Cash on Delivery: +{money(settings.DELIVERY_CHARGE_COD)} → "
        f"*{money(totals['cod_total'])}*\n"
        f"📱 Pay Online: +{money(settings.DELIVERY_CHARGE_ONLINE)} (online "
        f"discount!) → *{money(totals['online_total'])}*\n\n"
        f"📍 Deliver to: {state.get('address')} - {pincode}\n"
        f"👤 {state.get('patient_name')} | 📱 {state.get('phone_number')}\n\n"
        "How would you like to pay?"
    )
    state["quick_replies"] = PAYMENT_REPLIES
    return state
