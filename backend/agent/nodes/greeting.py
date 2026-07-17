"""
General / menu conversation handlers (everything reachable from idle that is
not prescription-OCR, pickup, delivery or payment):

    greeting, browse_catalog, search_medicine, place_order, list_stores,
    check_status, cancel_order, and the context-aware fallbacks.

Each handler is an async LangGraph-style node: it takes the state, mutates the
turn-output fields (reply_message / quick_replies / cards / response_type) and
any persistent fields (basket / current_step / order_type), and returns state.
"""
from __future__ import annotations

from typing import List

from agent.state import (
    FULFILMENT_REPLIES,
    MAIN_MENU_REPLIES,
    BasketItem,
    PharmacyState,
)
from services.database import db
from services.matching import resolve_medicine


def _rupees(value) -> str:
    try:
        n = float(value)
    except (TypeError, ValueError):
        return f"₹{value}"
    return f"₹{int(n)}" if n == int(n) else f"₹{n:.2f}"


def _norm(s: str) -> str:
    return "".join(c for c in (s or "").lower() if c.isalnum())


def _norm_differs(query: str, name: str) -> bool:
    """True if the matched name isn't essentially what the user typed."""
    a, b = _norm(query), _norm(name)
    return bool(a) and bool(b) and a not in b and b not in a


async def _resolve(query: str):
    """Fetch the catalogue + aliases and resolve a user's medicine text."""
    medicines = await db.get_medicines()
    aliases = await db.get_aliases()
    return resolve_medicine(query, medicines, aliases), medicines


def _did_you_mean(state: PharmacyState, query: str, options: List[dict]) -> PharmacyState:
    """Render a 'did you mean' prompt for a weak/ambiguous match."""
    opts = options[:4]
    lines = "\n".join(
        f"• *{o['name']}* — {_rupees(o.get('price'))}"
        + (" ⚠️ Rx" if o.get("requires_prescription") else "")
        for o in opts
    )
    state["response_type"] = "message"
    state["reply_message"] = (
        f"I couldn't find an exact match for *{query}*. Did you mean:\n\n{lines}"
    )
    state["quick_replies"] = [
        {"label": o["name"], "value": f"order {o['name']}"} for o in opts
    ]
    return state


# --------------------------------------------------------------------------
# greeting
# --------------------------------------------------------------------------
async def handle_greeting(state: PharmacyState) -> PharmacyState:
    name = state.get("display_name") or state.get("patient_name")
    hello = f"Hello {name}! 👋" if name else "Hello! 👋"
    state["response_type"] = "message"
    state["reply_message"] = (
        f"{hello} Welcome to *1Health Pharmacy*.\n\n"
        "Here's how to order:\n"
        "1️⃣ Type a medicine name or upload your prescription\n"
        "2️⃣ Choose Pickup or Delivery\n"
        "3️⃣ Share your details\n"
        "4️⃣ Confirm your order\n\n"
        "What would you like to do?"
    )
    state["quick_replies"] = MAIN_MENU_REPLIES
    return state


# --------------------------------------------------------------------------
# browse_catalog
# --------------------------------------------------------------------------
async def handle_browse_catalog(state: PharmacyState) -> PharmacyState:
    medicines = await db.get_medicines(in_stock_only=True)
    state["response_type"] = "message"
    if not medicines:
        state["reply_message"] = "Sorry, no medicines are available right now."
        state["quick_replies"] = MAIN_MENU_REPLIES
        return state

    lines = []
    for i, m in enumerate(medicines[:30], start=1):
        rx = " ⚠️ Rx" if m.get("requires_prescription") else ""
        brand = f" ({m['brand']})" if m.get("brand") else ""
        lines.append(f"{i}. *{m['name']}*{brand} — {_rupees(m.get('price'))}{rx}")

    state["reply_message"] = (
        "💊 *Available Medicines*\n\n"
        + "\n".join(lines)
        + "\n\nType a medicine name to order, or upload a prescription."
    )
    # Also surface as medicine cards for the UI.
    state["cards"] = [
        {
            "type": "medicine",
            "name": m["name"],
            "brand": m.get("brand"),
            "price": m.get("price"),
            "requires_prescription": bool(m.get("requires_prescription")),
        }
        for m in medicines[:30]
    ]
    return state


# --------------------------------------------------------------------------
# search_medicine
# --------------------------------------------------------------------------
async def handle_search_medicine(state: PharmacyState) -> PharmacyState:
    query = state.get("extracted_medicine") or state.get("input_text") or ""
    res, _ = await _resolve(query)
    state["response_type"] = "message"

    m = res["match"]
    if not m:
        state["reply_message"] = (
            f"Sorry, I couldn't find *{query}* in our catalogue.\n\n"
            "Type *catalog* to see everything we carry, or try a different name."
        )
        state["quick_replies"] = MAIN_MENU_REPLIES
        return state

    # Uncertain match -> confirm before committing to a product.
    if res["quality"] == "weak":
        options = [m] + res["alternatives"]
        return _did_you_mean(state, query, options)

    # Confident match -> show the product. Mention the correction if we adjusted.
    corrected_note = ""
    if _norm_differs(query, m["name"]):
        corrected_note = f"_(showing closest match for “{query}”)_\n\n"

    in_stock = (m.get("stock_quantity") or 0) > 0
    brand = f" ({m['brand']})" if m.get("brand") else ""
    rx_note = (
        "\n\n⚠️ This medicine requires a prescription. Please upload it to order."
        if m.get("requires_prescription")
        else ""
    )
    state["reply_message"] = (
        f"{corrected_note}*{m['name']}*{brand}\n\n"
        f"Price: {_rupees(m.get('price'))}\n"
        f"Category: {m.get('category') or 'General'}\n"
        f"Stock: {'Available ✅' if in_stock else 'Out of stock ❌'}"
        f"{rx_note}"
    )
    if in_stock and not m.get("requires_prescription"):
        state["quick_replies"] = [
            {"label": f"🛒 Order {m['name']}", "value": f"order {m['name']}"}
        ]
    elif m.get("requires_prescription"):
        state["quick_replies"] = [
            {"label": "📄 Upload prescription", "value": "upload_prescription"}
        ]
    return state


# --------------------------------------------------------------------------
# place_order  (typed order -> add to basket -> choose fulfilment)
# --------------------------------------------------------------------------
async def handle_place_order(state: PharmacyState) -> PharmacyState:
    query = state.get("extracted_medicine") or state.get("input_text") or ""
    if not query:
        return await handle_search_medicine(state)

    res, _ = await _resolve(query)
    state["response_type"] = "message"

    m = res["match"]
    if not m:
        state["reply_message"] = (
            f"Sorry, I couldn't find *{query}* in our catalogue.\n\n"
            "Type *catalog* to browse what we have, or try a different name."
        )
        state["quick_replies"] = MAIN_MENU_REPLIES
        return state

    # Uncertain match -> confirm which medicine before adding to the basket.
    if res["quality"] == "weak":
        return _did_you_mean(state, query, [m] + res["alternatives"])

    # Business rule (answer #5): prescription-only medicines cannot be added by
    # typing — the patient must upload a prescription first.
    if m.get("requires_prescription"):
        state["reply_message"] = (
            f"*{m['name']}* requires a valid prescription. 📄\n\n"
            "Please upload your prescription and I'll add it for you."
        )
        state["quick_replies"] = [
            {"label": "📄 Upload prescription", "value": "upload_prescription"}
        ]
        return state

    if (m.get("stock_quantity") or 0) <= 0:
        state["reply_message"] = (
            f"Sorry, *{m['name']}* is currently out of stock.\n\n"
            "Type *catalog* to see available medicines."
        )
        state["quick_replies"] = MAIN_MENU_REPLIES
        return state

    qty = state.get("extracted_quantity") or 1
    if qty < 1:
        qty = 1

    item: BasketItem = {
        "name": m["name"],
        "quantity": int(qty),
        "price": float(m.get("price") or 0),
    }
    # Single-item basket for a typed order (mirrors the Telegram bot).
    state["basket"] = [item]
    state["order_type"] = None
    state["payment_method"] = None

    line_total = item["price"] * item["quantity"]
    state["reply_message"] = (
        f"Added *{m['name']}* × {qty} = {_rupees(line_total)} to your basket. 🛒\n\n"
        "How would you like to receive it?"
    )
    state["quick_replies"] = FULFILMENT_REPLIES
    return state


# --------------------------------------------------------------------------
# list_stores
# --------------------------------------------------------------------------
async def handle_list_stores(state: PharmacyState) -> PharmacyState:
    stores = await db.get_stores()
    state["response_type"] = "message"
    if not stores:
        state["reply_message"] = "We couldn't load our store list right now."
        state["quick_replies"] = MAIN_MENU_REPLIES
        return state

    lines = []
    for i, s in enumerate(stores, start=1):
        hours = ""
        if s.get("opening_time") and s.get("closing_time"):
            hours = f"\n   🕒 {s['opening_time']} - {s['closing_time']}"
        lines.append(
            f"{i}. *{s['name']}*\n   📍 {s.get('address', '')}"
            f"\n   📞 {s.get('phone', '')}{hours}"
        )
    state["reply_message"] = (
        "🏪 *Our Stores*\n\n"
        + "\n\n".join(lines)
        + "\n\nUpload a prescription or type a medicine name to order."
    )
    state["cards"] = [
        {
            "type": "store",
            "name": s["name"],
            "address": s.get("address"),
            "phone": s.get("phone"),
            "hours": (
                f"{s.get('opening_time', '')} - {s.get('closing_time', '')}"
                if s.get("opening_time")
                else None
            ),
        }
        for s in stores
    ]
    return state


# --------------------------------------------------------------------------
# check_status
# --------------------------------------------------------------------------
async def handle_check_status(state: PharmacyState) -> PharmacyState:
    orders = await db.get_orders_by_chat(state["chat_id"], limit=3)
    state["response_type"] = "message"
    if not orders:
        state["reply_message"] = (
            "You have no orders yet. Type *catalog* to browse medicines."
        )
        state["quick_replies"] = MAIN_MENU_REPLIES
        return state

    lines = []
    for i, o in enumerate(orders, start=1):
        oid = str(o.get("id", ""))[:8]
        lines.append(
            f"{i}. Order {oid}…\n"
            f"   Status: {str(o.get('status', '')).upper()}\n"
            f"   Total: {_rupees(o.get('total_price'))}\n"
            f"   Type: {o.get('order_type', '-')}"
        )
    state["reply_message"] = "📦 *Your Recent Orders*\n\n" + "\n\n".join(lines)
    return state


# --------------------------------------------------------------------------
# cancel_order
# --------------------------------------------------------------------------
async def handle_cancel_order(state: PharmacyState) -> PharmacyState:
    state["basket"] = []
    state["current_step"] = "idle"
    state["order_type"] = None
    state["payment_method"] = None
    state["pincode"] = None
    state["response_type"] = "message"
    state["reply_message"] = (
        "Your order has been cancelled. 🗑️\n\n"
        "Type *catalog* to browse medicines or start a new order anytime."
    )
    state["quick_replies"] = MAIN_MENU_REPLIES
    return state


# --------------------------------------------------------------------------
# fallbacks
# --------------------------------------------------------------------------
async def handle_fallback(state: PharmacyState) -> PharmacyState:
    """unknown / uncovered intents while idle."""
    state["response_type"] = "message"
    # If the intent node already produced a friendly LLM reply, keep it.
    if not state.get("reply_message"):
        state["reply_message"] = (
            "I can help you order medicines, read a prescription, find our "
            "stores, or check your orders. What would you like to do?"
        )
    state["quick_replies"] = MAIN_MENU_REPLIES
    return state


async def handle_reconfirm(state: PharmacyState) -> PharmacyState:
    """Ambiguous answer at a yes/no confirmation step."""
    state["response_type"] = "message"
    state["reply_message"] = "Please reply *yes* to confirm or *no* to cancel."
    state["quick_replies"] = [
        {"label": "✅ Yes", "value": "yes"},
        {"label": "❌ No", "value": "no"},
    ]
    return state


async def handle_await_payment(state: PharmacyState) -> PharmacyState:
    """Message received while waiting for online payment (not 'PAID')."""
    state["response_type"] = "message"
    state["reply_message"] = (
        "Your payment link is still open. Once you've paid, your order will be "
        "confirmed automatically — or reply *PAID* if you've completed it."
    )
    return state


async def handle_upload_prescription_hint(state: PharmacyState) -> PharmacyState:
    state["response_type"] = "message"
    state["reply_message"] = (
        "Sure! Tap the 📎 attach button below and send a clear photo of your "
        "prescription. I'll read it and list the medicines for you."
    )
    return state
