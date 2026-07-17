"""
LangGraph state for the pharmacy conversation.

`PharmacyState` is a plain TypedDict that flows through every node. It is
hydrated from the Supabase `sessions` row at the start of each message and the
persistent fields are written back at the end (Supabase is the single source of
truth; see services/database.py and agent/graph.py).

Fields fall into three groups:
  1. Persistent  — mirror columns on the `sessions` table.
  2. Turn input  — the incoming message for this turn.
  3. Turn output — what the node layer produced for the frontend.
"""
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, TypedDict

# ---- Conversation steps (must match values stored in sessions.current_step) --
Step = Literal[
    "idle",
    # legacy typed-order COD path
    "collecting_name",
    "collecting_phone",
    "collecting_address",
    "confirming",
    # pickup path
    "pickup_collecting_name",
    "pickup_collecting_phone",
    "pickup_collecting_address",
    "pickup_selecting_store",
    # delivery path
    "delivery_collecting_name",
    "delivery_collecting_phone",
    "delivery_collecting_address",
    "delivery_collecting_pincode",
    "delivery_confirming",
    # online payment
    "online_payment_pending",
]

# ---- Response envelope types sent to the frontend over the WebSocket ---------
ResponseType = Literal[
    "message",
    "prescription_details",
    "store_list",
    "payment",
    "typing",
]

# ---- Message kinds coming in from the frontend -------------------------------
InputType = Literal["text", "image", "prescription", "button_click"]


class BasketItem(TypedDict, total=False):
    name: str
    quantity: int
    price: float
    dosage: str


class QuickReply(TypedDict):
    label: str
    value: str


class PharmacyState(TypedDict, total=False):
    # ------------------------------------------------------------------ #
    # 1. Persistent — loaded from / saved to the sessions table
    # ------------------------------------------------------------------ #
    chat_id: str                      # session id (web) == sessions.chat_id
    current_step: Step
    basket: List[BasketItem]
    patient_name: Optional[str]
    phone_number: Optional[str]
    address: Optional[str]
    pincode: Optional[str]
    order_type: Optional[Literal["pickup", "delivery"]]
    payment_method: Optional[Literal["cod", "online", "pickup"]]
    prescription_image_url: Optional[str]
    display_name: Optional[str]       # sessions.telegram_username

    # ------------------------------------------------------------------ #
    # 2. Turn input — the message being processed this turn
    # ------------------------------------------------------------------ #
    input_type: InputType
    input_text: str                   # raw text, or button value, or image url
    image_url: Optional[str]          # populated for image/prescription turns

    # Intent + extracted slots for this turn (set by the intent node)
    intent: str
    extracted_medicine: Optional[str]
    extracted_quantity: Optional[int]
    extracted_name: Optional[str]
    extracted_phone: Optional[str]
    extracted_address: Optional[str]
    extracted_pincode: Optional[str]

    # ------------------------------------------------------------------ #
    # 3. Turn output — consumed by api/chat.py to build the WS response
    # ------------------------------------------------------------------ #
    response_type: ResponseType
    reply_message: str
    quick_replies: List[QuickReply]
    cards: List[Dict[str, Any]]       # store cards / medicine cards
    prescription: Optional[Dict[str, Any]]
    payment_link: Optional[str]


# Default quick-reply button sets reused across nodes -------------------------
MAIN_MENU_REPLIES: List[QuickReply] = [
    {"label": "🛒 Browse medicines", "value": "catalog"},
    {"label": "📄 Upload prescription", "value": "upload_prescription"},
    {"label": "🏪 Our stores", "value": "list stores"},
    {"label": "📦 My orders", "value": "my orders"},
]

FULFILMENT_REPLIES: List[QuickReply] = [
    {"label": "🏪 Pickup", "value": "pickup"},
    {"label": "🚚 Delivery", "value": "delivery"},
]

PAYMENT_REPLIES: List[QuickReply] = [
    {"label": "💵 Cash on Delivery", "value": "cod"},
    {"label": "📱 Pay Online", "value": "online"},
]


def new_turn_output() -> Dict[str, Any]:
    """A blank turn-output block; nodes fill in what they need."""
    return {
        "response_type": "message",
        "reply_message": "",
        "quick_replies": [],
        "cards": [],
        "prescription": None,
        "payment_link": None,
    }
