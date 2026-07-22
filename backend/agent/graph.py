"""
LangGraph state machine.

Shape: a single `detect_intent` entry node, then a conditional fan-out to one
handler per intent, each terminating at END. Every handler fully builds the
turn output, so the graph runs exactly one hop per message.

Persistence is external (Supabase, via api/chat.py) — no checkpointer here.
"""
from __future__ import annotations

from langgraph.graph import END, StateGraph

from agent.state import PAYMENT_REPLIES, PharmacyState
from agent.nodes.intent import detect_intent
from agent.nodes import greeting as g
from agent.nodes import prescription as rx
from agent.nodes import pickup as pk
from agent.nodes import delivery as dl
from agent.nodes import payment as pay


async def _prompt_payment(state: PharmacyState) -> PharmacyState:
    """delivery_confirm (typed yes at delivery_confirming): ask for a method."""
    state["response_type"] = "message"
    state["reply_message"] = "Please choose how you'd like to pay:"
    state["quick_replies"] = PAYMENT_REPLIES
    return state


# intent -> handler node
NODES = {
    # general / menu
    "greeting": g.handle_greeting,
    "browse_catalog": g.handle_browse_catalog,
    "search_medicine": g.handle_search_medicine,
    "place_order": g.handle_place_order,
    "provide_quantity": g.handle_provide_quantity,
    "list_stores": g.handle_list_stores,
    "check_status": g.handle_check_status,
    "cancel_order": g.handle_cancel_order,
    "upload_prescription_hint": g.handle_upload_prescription_hint,
    "fallback": g.handle_fallback,
    "reconfirm": g.handle_reconfirm,
    "await_payment": g.handle_await_payment,
    # prescription OCR
    "prescription_upload": rx.handle_prescription,
    # pickup
    "select_pickup": pk.handle_select_pickup,
    "pickup_provide_name": pk.handle_pickup_name,
    "pickup_provide_phone": pk.handle_pickup_phone,
    "pickup_provide_address": pk.handle_pickup_address,
    "pickup_select_store": pk.handle_pickup_select_store,
    # delivery
    "select_delivery": dl.handle_select_delivery,
    "delivery_provide_name": dl.handle_delivery_name,
    "delivery_provide_phone": dl.handle_delivery_phone,
    "delivery_provide_address": dl.handle_delivery_address,
    "delivery_provide_pincode": dl.handle_delivery_pincode,
    "delivery_confirm": _prompt_payment,
    # payment
    "pay_cod": pay.handle_pay_cod,
    "pay_online": pay.handle_pay_online,
    "online_payment_confirm": pay.handle_online_payment_confirm,
}

# Legacy typed-COD intents are unreachable in the button-driven web flow; send
# them to the friendly fallback rather than dead-ending.
_ALIAS_TO_FALLBACK = {
    "provide_name": "fallback",
    "provide_phone": "fallback",
    "provide_address": "fallback",
    "confirm_order": "fallback",
    "unknown": "fallback",
}


def _route(state: PharmacyState) -> str:
    intent = state.get("intent", "unknown")
    if intent in NODES:
        return intent
    return _ALIAS_TO_FALLBACK.get(intent, "fallback")


def build_graph():
    graph = StateGraph(PharmacyState)
    graph.add_node("detect_intent", detect_intent)
    for name, fn in NODES.items():
        graph.add_node(name, fn)

    graph.set_entry_point("detect_intent")
    graph.add_conditional_edges(
        "detect_intent", _route, {name: name for name in NODES}
    )
    for name in NODES:
        graph.add_edge(name, END)
    return graph.compile()


# Compiled once at import; reused for every message.
pharmacy_graph = build_graph()


async def run_turn(state: PharmacyState) -> PharmacyState:
    """Run one conversation turn through the graph and return the final state."""
    return await pharmacy_graph.ainvoke(state)
