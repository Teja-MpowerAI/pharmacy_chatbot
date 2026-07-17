"""
In-process pub/sub bus for pushing messages into live WebSocket sessions.

Used by:
  * api/chat.py                — SUBSCRIBES a queue per open WebSocket
  * api/dashboard.py           — PUBLISHES admin confirm/reject
  * api/webhooks/supabase.py   — PUBLISHES order-status-change notifications
  * api/webhooks/razorpay.py   — PUBLISHES payment-success notifications

The chatbot runs as a single uvicorn process, so an in-memory fan-out delivers
reliably without an external broker. This intentionally replaces the earlier
Redis dependency (which was blocking local delivery). If the app is ever scaled
to multiple worker processes, reintroduce a cross-process broker (e.g. Redis)
here — the public API (subscribe / unsubscribe / publish_to_session) can stay
the same.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, Set

logger = logging.getLogger(__name__)

# session_id -> set of subscriber queues (one per open WebSocket for that session)
_subscribers: Dict[str, Set["asyncio.Queue[Dict[str, Any]]"]] = {}


def subscribe(session_id: str) -> "asyncio.Queue[Dict[str, Any]]":
    q: "asyncio.Queue[Dict[str, Any]]" = asyncio.Queue()
    _subscribers.setdefault(session_id, set()).add(q)
    return q


def unsubscribe(session_id: str, q: "asyncio.Queue[Dict[str, Any]]") -> None:
    subs = _subscribers.get(session_id)
    if subs:
        subs.discard(q)
        if not subs:
            _subscribers.pop(session_id, None)


async def publish_to_session(session_id: str, payload: Dict[str, Any]) -> None:
    """Deliver a WebSocket-shaped payload to every open socket for a session."""
    subs = _subscribers.get(session_id)
    if not subs:
        logger.info("No active session %s to deliver push message to.", session_id)
        return
    for q in list(subs):
        try:
            q.put_nowait(payload)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to enqueue push for %s: %s", session_id, exc)


async def close_bus() -> None:
    """Lifespan hook; nothing to tear down for the in-process bus."""
    _subscribers.clear()
