"""
Prescription OCR node.

Flow (answer #6):
  frontend uploads image -> /api/chat/upload-image -> Supabase Storage
  frontend sends WS {"type":"prescription","content": <public_url>}
  api/chat.py sets state.image_url and routes here.

This node feeds the public image URL to GPT-4o Vision, parses the returned JSON,
stores the extracted prescription on the state, and builds a price-less basket
(name / dosage / quantity) so the delivery minimum-order rule can distinguish a
prescription order from a typed one.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

from config import settings
from agent.state import FULFILMENT_REPLIES, MAIN_MENU_REPLIES, PharmacyState

logger = logging.getLogger(__name__)

_vision = ChatOpenAI(
    model=settings.OPENAI_VISION_MODEL,
    api_key=settings.OPENAI_API_KEY,
    temperature=0,
    max_tokens=1500,
)

_OCR_PROMPT = """This is a medical prescription image. Extract all details carefully.

Return ONLY a valid JSON object. No explanation, no markdown, no code fences:
{
  "patient_name": "patient name if visible, else null",
  "doctor_name": "doctor name if visible, else null",
  "hospital_name": "hospital or clinic name if visible, else null",
  "prescription_date": "date in DD/MM/YYYY if visible, else null",
  "medicines": [
    {
      "name": "medicine name",
      "dosage": "e.g. 625mg",
      "frequency": "e.g. 1-0-1 or twice daily",
      "duration": "e.g. 5 days",
      "quantity": 10
    }
  ]
}

If you cannot read it, return exactly: {"error": "Cannot read prescription clearly"}
Return only the JSON object, starting with { and ending with }."""


def _clean_json(raw: str) -> Dict[str, Any]:
    cleaned = (raw or "").replace("```json", "").replace("```", "").strip()
    return json.loads(cleaned)


async def _read_prescription(image_url: str) -> Dict[str, Any]:
    message = HumanMessage(
        content=[
            {"type": "text", "text": _OCR_PROMPT},
            {"type": "image_url", "image_url": {"url": image_url}},
        ]
    )
    resp = await _vision.ainvoke([message])
    return _clean_json(resp.content)


def _format_details(parsed: Dict[str, Any]) -> str:
    header = []
    if parsed.get("patient_name"):
        header.append(f"👤 *Patient:* {parsed['patient_name']}")
    if parsed.get("doctor_name"):
        header.append(f"🩺 *Doctor:* {parsed['doctor_name']}")
    if parsed.get("hospital_name"):
        header.append(f"🏥 *Hospital:* {parsed['hospital_name']}")
    if parsed.get("prescription_date"):
        header.append(f"📅 *Date:* {parsed['prescription_date']}")
    header_text = ("\n".join(header) + "\n\n") if header else ""

    meds = parsed.get("medicines") or []
    lines = []
    for i, m in enumerate(meds, start=1):
        line = f"{i}. *{m.get('name', 'Unknown')}*"
        if m.get("dosage"):
            line += f"\n   💊 Dosage: {m['dosage']}"
        if m.get("frequency"):
            line += f"\n   🔁 Frequency: {m['frequency']}"
        if m.get("duration"):
            line += f"\n   ⏳ Duration: {m['duration']}"
        if m.get("quantity"):
            line += f"\n   📦 Quantity: {m['quantity']}"
        lines.append(line)

    return (
        "📄 *Prescription Details*\n\n"
        + header_text
        + "💊 *Medicines Prescribed:*\n\n"
        + "\n\n".join(lines)
        + "\n\nWould you like *Pickup* from a store or *Home Delivery*?"
    )


async def handle_prescription(state: PharmacyState) -> PharmacyState:
    image_url = state.get("image_url") or state.get("input_text")
    state["response_type"] = "message"

    if not image_url:
        state["reply_message"] = (
            "I didn't receive an image. Please tap 📎 and send a clear photo of "
            "your prescription."
        )
        state["quick_replies"] = MAIN_MENU_REPLIES
        return state

    try:
        parsed = await _read_prescription(image_url)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Prescription OCR failed: %s", exc)
        parsed = {"error": "Cannot read prescription"}

    medicines = parsed.get("medicines") or []
    if parsed.get("error") or not medicines:
        state["reply_message"] = (
            "Sorry, I couldn't read your prescription clearly. 😔\n\n"
            "Please send a clearer, well-lit photo, or type the medicine names "
            "manually."
        )
        state["quick_replies"] = MAIN_MENU_REPLIES
        return state

    # Persist the image URL and a PRICE-LESS basket (prescription order marker).
    state["prescription_image_url"] = image_url
    state["basket"] = [
        {
            "name": m.get("name", "").strip(),
            "dosage": m.get("dosage", "") or "",
            "quantity": int(m["quantity"]) if str(m.get("quantity", "")).isdigit() else 1,
        }
        for m in medicines
        if m.get("name")
    ]
    state["order_type"] = None
    state["payment_method"] = None
    state["current_step"] = "idle"  # buttons drive the next step

    state["response_type"] = "prescription_details"
    state["reply_message"] = _format_details(parsed)
    state["prescription"] = {
        "patient_name": parsed.get("patient_name"),
        "doctor_name": parsed.get("doctor_name"),
        "hospital_name": parsed.get("hospital_name"),
        "prescription_date": parsed.get("prescription_date"),
        "medicines": medicines,
        "image_url": image_url,
    }
    state["quick_replies"] = FULFILMENT_REPLIES
    return state
