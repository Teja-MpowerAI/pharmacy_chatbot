"""
Chat API: prescription image upload + the real-time WebSocket endpoint.

WebSocket contract
------------------
Client -> server:
  {"type": "text",         "content": "I want Augmentin"}
  {"type": "button_click", "content": "pickup"}
  {"type": "prescription", "content": "https://...supabase.co/.../rx.jpg"}
  {"type": "image",        "content": "<base64>"}   # alt to upload endpoint

Server -> client:
  {"type": "typing", "content": true|false}
  {"type": "message"|"store_list"|"prescription_details"|"payment",
   "content": "...", "quick_replies": [...], "cards": [...],
   "prescription": {...}?, "payment_link": "..."?}

Session state lives in Supabase (single source of truth): it is hydrated into
the LangGraph state before each turn and written back after.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict

from fastapi import APIRouter, File, UploadFile, WebSocket, WebSocketDisconnect

from agent.graph import run_turn
from agent.state import new_turn_output
from services.database import db, dumps_json, loads_json
from services.pubsub import subscribe, unsubscribe
from services.storage import upload_prescription

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/chat", tags=["chat"])

# Persistent state fields that mirror columns on the `sessions` table.
_PERSIST_FIELDS = (
    "current_step",
    "patient_name",
    "phone_number",
    "address",
    "pincode",
    "prescription_image_url",
)


# --------------------------------------------------------------------------
# Image upload (answer #6): multipart -> Supabase Storage -> public URL
# --------------------------------------------------------------------------
@router.post("/upload-image")
async def upload_image(file: UploadFile = File(...), session_id: str = ""):
    content = await file.read()
    url = await upload_prescription(
        content, content_type=file.content_type or "image/jpeg", chat_id=session_id or None
    )
    return {"image_url": url}


# --------------------------------------------------------------------------
# State <-> session mapping
# --------------------------------------------------------------------------
def _session_to_state(session: Dict[str, Any]) -> Dict[str, Any]:
    state = new_turn_output()
    state.update(
        {
            "chat_id": str(session.get("chat_id")),
            "current_step": session.get("current_step") or "idle",
            "basket": loads_json(session.get("basket"), []),
            "patient_name": session.get("patient_name"),
            "phone_number": session.get("phone_number"),
            "address": session.get("address"),
            "pincode": session.get("pincode"),
            "prescription_image_url": session.get("prescription_image_url"),
            "display_name": session.get("telegram_username"),
            "order_type": None,
            "payment_method": None,
        }
    )
    return state


async def _save_state(state: Dict[str, Any]) -> None:
    fields = {k: state.get(k) for k in _PERSIST_FIELDS}
    fields["basket"] = dumps_json(state.get("basket", []))
    await db.update_session(state["chat_id"], fields)


def _build_response(state: Dict[str, Any]) -> Dict[str, Any]:
    payload = {
        "type": state.get("response_type", "message"),
        "content": state.get("reply_message", ""),
        "quick_replies": state.get("quick_replies", []),
        "cards": state.get("cards", []),
    }
    if state.get("prescription") is not None:
        payload["prescription"] = state["prescription"]
    if state.get("payment_link"):
        payload["payment_link"] = state["payment_link"]
    return payload


def _apply_incoming(state: Dict[str, Any], message: Dict[str, Any]) -> None:
    mtype = message.get("type", "text")
    content = message.get("content", "")
    if mtype == "prescription":
        state["input_type"] = "prescription"
        state["image_url"] = content
        state["input_text"] = content
    elif mtype == "image":
        # base64 body -> data URL that GPT-4o Vision accepts directly
        data_url = content
        if content and not str(content).startswith("data:"):
            data_url = f"data:image/jpeg;base64,{content}"
        state["input_type"] = "image"
        state["image_url"] = data_url
        state["input_text"] = ""
    elif mtype == "button_click":
        state["input_type"] = "button_click"
        state["input_text"] = str(content)
    else:
        state["input_type"] = "text"
        state["input_text"] = str(content)


# --------------------------------------------------------------------------
# Fan-in: forward admin / payment / order-status push messages to this socket
# --------------------------------------------------------------------------
async def _push_forwarder(websocket: WebSocket, session_id: str) -> None:
    """Deliver in-process pushed messages (admin confirm/reject, payment,
    order-status webhook) to this WebSocket as they arrive."""
    q = subscribe(session_id)
    try:
        while True:
            payload = await q.get()
            await websocket.send_json(payload)
    except asyncio.CancelledError:
        pass
    except Exception as exc:  # noqa: BLE001
        logger.warning("Push forwarder stopped for %s: %s", session_id, exc)
    finally:
        unsubscribe(session_id, q)


# --------------------------------------------------------------------------
# WebSocket endpoint
# --------------------------------------------------------------------------
@router.websocket("/ws/{session_id}")
async def chat_ws(websocket: WebSocket, session_id: str):
    await websocket.accept()
    await db.get_or_create_session(session_id)

    forwarder = asyncio.create_task(_push_forwarder(websocket, session_id))

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                message = json.loads(raw)
            except json.JSONDecodeError:
                message = {"type": "text", "content": raw}

            await websocket.send_json({"type": "typing", "content": True})

            try:
                session = await db.get_or_create_session(session_id)
                state = _session_to_state(session)
                _apply_incoming(state, message)
                state = await run_turn(state)
                await _save_state(state)
                response = _build_response(state)
            except Exception as exc:  # noqa: BLE001
                logger.exception("Turn failed for %s: %s", session_id, exc)
                response = {
                    "type": "message",
                    "content": "Sorry, something went wrong. Please try again.",
                    "quick_replies": [],
                    "cards": [],
                }

            await websocket.send_json({"type": "typing", "content": False})
            await websocket.send_json(response)

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected: %s", session_id)
    finally:
        forwarder.cancel()
        try:
            await forwarder
        except asyncio.CancelledError:
            pass
