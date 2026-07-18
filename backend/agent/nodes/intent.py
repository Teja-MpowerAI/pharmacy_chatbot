"""
Intent detection.

Two-layer design (per product spec):

  * If `current_step` is NOT idle, the step itself determines the intent. We do
    NOT call the LLM — the user is mid-flow filling a slot, so we route
    deterministically and extract the one value we need. This is faster,
    cheaper and immune to the classifier "changing its mind" mid-order.

  * If `current_step` IS idle, we call GPT-4o-mini once to classify the message
    into a small set of entry intents and extract a medicine/quantity if present.

Button clicks are always authoritative and bypass both layers.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, Optional

from langchain_openai import ChatOpenAI

from config import settings
from agent.state import PharmacyState

logger = logging.getLogger(__name__)

_llm = ChatOpenAI(
    model=settings.OPENAI_INTENT_MODEL,
    api_key=settings.OPENAI_API_KEY,
    temperature=0,
)

# Button value -> intent. Buttons are deterministic commands.
BUTTON_INTENT: Dict[str, str] = {
    "pickup": "select_pickup",
    "delivery": "select_delivery",
    "cod": "pay_cod",
    "online": "pay_online",
    "catalog": "browse_catalog",
    "list stores": "list_stores",
    "my orders": "check_status",
    "upload_prescription": "upload_prescription_hint",
    "cancel": "cancel_order",
}

# Affirmative / negative tokens for yes-no steps (English + common Hinglish).
_YES = {"yes", "y", "ok", "okay", "confirm", "confirmed", "sure", "haan", "ha", "haa"}
_NO = {"no", "n", "cancel", "nahi", "nope", "stop"}

# current_step -> intent for the deterministic (non-idle) layer.
STEP_INTENT: Dict[str, str] = {
    "collecting_quantity": "provide_quantity",
    "collecting_name": "provide_name",
    "collecting_phone": "provide_phone",
    "collecting_address": "provide_address",
    "pickup_collecting_name": "pickup_provide_name",
    "pickup_collecting_phone": "pickup_provide_phone",
    "pickup_collecting_address": "pickup_provide_address",
    "pickup_selecting_store": "pickup_select_store",
    "delivery_collecting_name": "delivery_provide_name",
    "delivery_collecting_phone": "delivery_provide_phone",
    "delivery_collecting_address": "delivery_provide_address",
    "delivery_collecting_pincode": "delivery_provide_pincode",
}

_INTENT_SYSTEM_PROMPT = """You are the intent classifier for an Indian pharmacy \
website chatbot. The user is at the start of a conversation (no order in \
progress). Classify their message and extract a medicine if one is named.

Return ONLY a valid JSON object, no markdown, no code fences:
{
  "intent": "one of: greeting, browse_catalog, search_medicine, place_order, list_stores, check_status, cancel_order, unknown",
  "extracted_medicine": "medicine name if the user names one, else null",
  "extracted_quantity": "integer number of tablets/units ONLY if clearly stated, else null",
  "reply": "a short friendly reply, max 2 sentences"
}

Rules:
- "order", "buy", "want", "I need" + a medicine name => place_order.
- "do you have", "is X available", "search", "find", "looking for" => search_medicine.
- "show", "list", "catalog", "medicines", "what do you have" => browse_catalog.
- "medical store", "which stores", "store list", "nearby store", "pharmacy near" => list_stores.
- "hi", "hello", "hey", "start", "help", "how to order" => greeting.
- "my order", "order status", "track", "where is my order" => check_status.
- "cancel" => cancel_order.
- extracted_quantity is a COUNT of tablets/units only. Never treat a rupee \
amount as a quantity (e.g. "for 500 rupees" => null).
- If unsure, use "unknown".
"""


def _digits(text: str) -> str:
    return re.sub(r"\D", "", text or "")


def _extract_phone(text: str) -> Optional[str]:
    """First 10-digit run, ignoring a leading +91/0."""
    d = _digits(text)
    if len(d) >= 12 and d.startswith("91"):
        d = d[2:]
    if len(d) == 11 and d.startswith("0"):
        d = d[1:]
    m = re.search(r"\d{10}", d)
    return m.group(0) if m else (d or None)


def _extract_pincode(text: str) -> Optional[str]:
    m = re.search(r"\b(\d{6})\b", text or "")
    if m:
        return m.group(1)
    d = _digits(text)
    return d if len(d) == 6 else None


def _extract_store_number(text: str) -> Optional[int]:
    m = re.search(r"\d+", text or "")
    return int(m.group(0)) if m else None


def _clean_json(raw: str) -> Dict[str, Any]:
    cleaned = raw.replace("```json", "").replace("```", "").strip()
    return json.loads(cleaned)


async def _classify_idle(text: str) -> Dict[str, Any]:
    """Call GPT-4o-mini to classify an idle-state message."""
    try:
        resp = await _llm.ainvoke(
            [
                {"role": "system", "content": _INTENT_SYSTEM_PROMPT},
                {"role": "user", "content": text or ""},
            ]
        )
        parsed = _clean_json(resp.content)
    except Exception as exc:  # noqa: BLE001 — never let classification crash a turn
        logger.exception("Intent classification failed: %s", exc)
        return {
            "intent": "unknown",
            "extracted_medicine": None,
            "extracted_quantity": None,
            "reply": "Sorry, I didn't quite get that. You can browse medicines, "
            "upload a prescription, or ask for our stores.",
        }

    qty = parsed.get("extracted_quantity")
    try:
        qty = int(qty) if qty not in (None, "", "null") else None
    except (TypeError, ValueError):
        qty = None

    return {
        "intent": parsed.get("intent", "unknown"),
        "extracted_medicine": parsed.get("extracted_medicine") or None,
        "extracted_quantity": qty,
        "reply": parsed.get("reply", ""),
    }


async def detect_intent(state: PharmacyState) -> PharmacyState:
    """
    LangGraph node: populate `intent` and the `extracted_*` slots on the state.
    Does not send anything — downstream handler nodes do that.
    """
    step = state.get("current_step", "idle")
    input_type = state.get("input_type", "text")
    text = (state.get("input_text") or "").strip()

    # Reset per-turn extraction slots.
    state.update(
        {
            "intent": "unknown",
            "extracted_medicine": None,
            "extracted_quantity": None,
            "extracted_name": None,
            "extracted_phone": None,
            "extracted_address": None,
            "extracted_pincode": None,
        }
    )

    # ---- 0. Image / prescription turns are handled by their own node -------
    if input_type in ("image", "prescription"):
        state["intent"] = "prescription_upload"
        return state

    # ---- 1. Button clicks: known commands are authoritative ----------------
    # An unmapped button value (e.g. a store number "1", a "yes", or
    # "order Augmentin") falls through and is handled exactly like typed text,
    # so step-routing / the LLM still apply.
    if input_type == "button_click":
        mapped = BUTTON_INTENT.get(text.lower())
        if mapped:
            state["intent"] = mapped
            return state
        # else: continue below, treating `text` as a normal message.

    # A universal escape hatch: typing "cancel" aborts any flow.
    if text.lower() in _NO and step not in ("delivery_confirming", "confirming"):
        if text.lower() == "cancel":
            state["intent"] = "cancel_order"
            return state

    # ---- 2. Deterministic step routing (no LLM) ----------------------------
    if step in STEP_INTENT:
        intent = STEP_INTENT[step]
        state["intent"] = intent
        if intent.endswith("provide_name"):
            state["extracted_name"] = text
        elif intent.endswith("provide_phone"):
            state["extracted_phone"] = _extract_phone(text)
        elif intent.endswith("provide_address"):
            state["extracted_address"] = text
        elif intent == "delivery_provide_pincode":
            state["extracted_pincode"] = _extract_pincode(text)
        elif intent == "pickup_select_store":
            state["extracted_quantity"] = _extract_store_number(text)
        elif intent == "provide_quantity":
            state["extracted_quantity"] = _extract_store_number(text)
        return state

    if step in ("delivery_confirming", "confirming"):
        low = text.lower()
        if any(tok in low.split() for tok in _YES) or low in _YES:
            state["intent"] = (
                "delivery_confirm" if step == "delivery_confirming" else "confirm_order"
            )
        elif any(tok in low.split() for tok in _NO) or low in _NO:
            state["intent"] = "cancel_order"
        else:
            state["intent"] = "reconfirm"  # ambiguous -> re-prompt
        return state

    if step == "online_payment_pending":
        if "paid" in text.lower() or "done" in text.lower():
            state["intent"] = "online_payment_confirm"
        else:
            state["intent"] = "await_payment"  # gently remind
        return state

    # ---- 3. Idle -> call the LLM classifier --------------------------------
    result = await _classify_idle(text)
    state["intent"] = result["intent"]
    state["extracted_medicine"] = result["extracted_medicine"]
    state["extracted_quantity"] = result["extracted_quantity"]
    # Stash the LLM's friendly reply for greeting/unknown handlers to reuse.
    state["reply_message"] = result.get("reply", "")
    return state
