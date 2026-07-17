"""
Pickup flow.

Steps: select_pickup -> pickup_collecting_name -> pickup_collecting_phone ->
pickup_selecting_store -> order created.

Fixes vs the n8n bot:
  * No stray address step (pickup is name -> phone -> stores, per spec).
  * Store selection reads the real `stores` table in a STABLE order (by id) and
    indexes into it, instead of a hardcoded 5-element JS array that could point
    the order at a different store than the patient saw.
  * Pickup pricing uses the selected store's own inventory price.
"""
from __future__ import annotations

from typing import Any, Dict, List

from agent.state import MAIN_MENU_REPLIES, PharmacyState
from services.database import db
from services.matching import fuzzy_match


def money(value) -> str:
    try:
        n = float(value)
    except (TypeError, ValueError):
        return f"₹{value}"
    return f"₹{int(n)}" if n == int(n) else f"₹{n:.2f}"


def _basket_names_qty(basket: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [
        {"name": i.get("name", ""), "quantity": int(i.get("quantity") or 1)}
        for i in basket
        if i.get("name")
    ]


def _build_store_entries(
    stores: List[Dict[str, Any]],
    inventory: List[Dict[str, Any]],
    basket: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    For each store compute availability + total price for the basket, using that
    store's inventory rows. Returns entries in the same order as `stores`.
    """
    wanted = _basket_names_qty(basket)
    entries: List[Dict[str, Any]] = []

    for idx, store in enumerate(stores, start=1):
        store_inv = [r for r in inventory if r.get("store_id") == store.get("id")]
        available = 0
        total_price = 0.0
        priced_items: List[Dict[str, Any]] = []

        for w in wanted:
            match = next(
                (
                    r
                    for r in store_inv
                    if fuzzy_match(r.get("medicine_name", ""), w["name"])
                ),
                None,
            )
            if match and (match.get("stock_quantity") or 0) > 0:
                available += 1
                price = float(match.get("price") or 0)
                line = price * w["quantity"]
                total_price += line
                priced_items.append(
                    {"name": w["name"], "quantity": w["quantity"], "price": price}
                )
            else:
                priced_items.append(
                    {"name": w["name"], "quantity": w["quantity"], "price": 0.0, "out_of_stock": True}
                )

        hours = (
            f"{store.get('opening_time', '')} - {store.get('closing_time', '')}"
            if store.get("opening_time")
            else None
        )
        entries.append(
            {
                "index": idx,
                "id": store.get("id"),
                "name": store.get("name"),
                "address": store.get("address"),
                "phone": store.get("phone"),
                "hours": hours,
                "available_count": available,
                "total_medicines": len(wanted),
                "total_price": total_price,
                "all_available": available == len(wanted) and len(wanted) > 0,
                "priced_items": priced_items,
            }
        )
    return entries


def _recommend(entries: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Most medicines available; tie-break on lower total price."""
    best = entries[0]
    for e in entries[1:]:
        if e["available_count"] > best["available_count"]:
            best = e
        elif (
            e["available_count"] == best["available_count"]
            and e["total_price"] < best["total_price"]
        ):
            best = e
    return best


# --------------------------------------------------------------------------
# select_pickup  (button)
# --------------------------------------------------------------------------
async def handle_select_pickup(state: PharmacyState) -> PharmacyState:
    if not state.get("basket"):
        state["response_type"] = "message"
        state["reply_message"] = (
            "Your basket is empty. Add a medicine or upload a prescription first. 🛒"
        )
        state["quick_replies"] = MAIN_MENU_REPLIES
        return state

    state["order_type"] = "pickup"
    state["payment_method"] = "pickup"
    state["current_step"] = "pickup_collecting_name"
    state["response_type"] = "message"
    state["reply_message"] = (
        "Great, *Pickup* from store selected! 🏪\n\nPlease tell me your *full name*."
    )
    return state


# --------------------------------------------------------------------------
# pickup_collecting_name
# --------------------------------------------------------------------------
async def handle_pickup_name(state: PharmacyState) -> PharmacyState:
    name = (state.get("extracted_name") or state.get("input_text") or "").strip()
    state["patient_name"] = name
    state["current_step"] = "pickup_collecting_phone"
    state["response_type"] = "message"
    state["reply_message"] = (
        f"Thank you *{name}*! 🙏\n\nWhat's your *phone number*? We'll call when "
        "your order is ready for pickup."
    )
    return state


# --------------------------------------------------------------------------
# pickup_collecting_phone -> show stores
# --------------------------------------------------------------------------
async def handle_pickup_phone(state: PharmacyState) -> PharmacyState:
    phone = state.get("extracted_phone")
    if not phone or len(phone) < 10:
        state["response_type"] = "message"
        state["reply_message"] = "Please send a valid 10-digit phone number. 📱"
        return state

    state["phone_number"] = phone

    stores = await db.get_stores()
    inventory = await db.get_store_inventory()
    if not stores:
        state["response_type"] = "message"
        state["reply_message"] = "Sorry, we couldn't load our stores right now."
        state["quick_replies"] = MAIN_MENU_REPLIES
        return state

    entries = _build_store_entries(stores, inventory, state.get("basket", []))

    lines = []
    for e in entries:
        med_lines = []
        for pi in e["priced_items"]:
            if pi.get("out_of_stock"):
                med_lines.append(f"   ❌ {pi['name']} ×{pi['quantity']} — Out of stock")
            else:
                med_lines.append(
                    f"   ✅ {pi['name']} ×{pi['quantity']} = {money(pi['price'] * pi['quantity'])}"
                )
        block = (
            f"{e['index']}. *{e['name']}*\n   📍 {e['address']}\n   📞 {e['phone']}"
            + (f"\n   🕒 {e['hours']}" if e["hours"] else "")
            + ("\n" + "\n".join(med_lines) if med_lines else "")
            + f"\n   📦 {e['available_count']}/{e['total_medicines']} available"
            + (f"\n   💰 Total: {money(e['total_price'])}" if e["total_price"] else "")
            + ("\n   ⭐ All medicines available" if e["all_available"] else "")
        )
        lines.append(block)

    rec = _recommend(entries)
    suggestion = (
        f"\n\n🤖 *Recommended:* {rec['name']} — {rec['available_count']}/"
        f"{rec['total_medicines']} available"
        + (f" at {money(rec['total_price'])}" if rec["total_price"] else "")
        if rec["available_count"] > 0
        else "\n\n⚠️ None of the stores have all your medicines in stock."
    )

    state["current_step"] = "pickup_selecting_store"
    state["response_type"] = "store_list"
    state["reply_message"] = (
        "🏪 *Select a Pickup Store*\n\n"
        + "\n\n".join(lines)
        + suggestion
        + "\n\nReply with the store *number* to select."
    )
    state["cards"] = [
        {
            "type": "store",
            "index": e["index"],
            "name": e["name"],
            "address": e["address"],
            "phone": e["phone"],
            "hours": e["hours"],
            "available_count": e["available_count"],
            "total_medicines": e["total_medicines"],
            "total_price": e["total_price"],
            "all_available": e["all_available"],
            "recommended": e["index"] == rec["index"] and rec["available_count"] > 0,
        }
        for e in entries
    ]
    state["quick_replies"] = [
        {"label": str(e["index"]), "value": str(e["index"])} for e in entries
    ]
    return state


# --------------------------------------------------------------------------
# pickup_selecting_store -> create order
# --------------------------------------------------------------------------
async def handle_pickup_select_store(state: PharmacyState) -> PharmacyState:
    number = state.get("extracted_quantity")
    stores = await db.get_stores()
    inventory = await db.get_store_inventory()

    if not number or number < 1 or number > len(stores):
        state["response_type"] = "message"
        state["reply_message"] = (
            f"Please reply with a store number between 1 and {len(stores)}."
        )
        return state

    entries = _build_store_entries(stores, inventory, state.get("basket", []))
    chosen = entries[number - 1]

    items = [
        pi for pi in chosen["priced_items"]  # includes prices from this store
    ]
    total = chosen["total_price"]

    order = await db.create_order(
        {
            "chat_id": state["chat_id"],
            "patient_name": state.get("patient_name"),
            "phone_number": state.get("phone_number"),
            "address": f"{chosen['name']}, {chosen['address']}",
            "items": items,
            "total_price": total,
            "status": "pending",
            "order_type": "pickup",
            "payment_method": "pickup",
            "prescription_image_url": state.get("prescription_image_url"),
        }
    )

    # Reset the working session (keep identity + lifetime counters).
    state["basket"] = []
    state["current_step"] = "idle"
    state["order_type"] = None
    state["pincode"] = None

    order_id = str(order.get("id", ""))[:8]
    item_lines = "\n".join(
        f"• {i['name']} ×{i['quantity']} = {money(i['price'] * i['quantity'])}"
        for i in items
        if not i.get("out_of_stock")
    )
    state["response_type"] = "message"
    state["reply_message"] = (
        f"🎉 *Order Received!*\n\nHi *{state.get('patient_name')}*, your pickup "
        f"order is placed.\n\n🏪 *Store:* {chosen['name']}\n📍 {chosen['address']}\n\n"
        f"📦 *Items:*\n{item_lines}\n\n💰 *Total: {money(total)}*\n"
        f"🧾 Order ID: {order_id}\n\n"
        "⏳ Our pharmacy team is reviewing your order. You'll get a confirmation "
        "message once it's accepted.\n\nThank you for choosing 1Health Pharmacy! 💊"
    )
    return state
