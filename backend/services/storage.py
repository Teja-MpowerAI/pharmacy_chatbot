"""
Supabase Storage operations for prescription images.

The frontend uploads the raw file to `POST /api/chat/upload-image`; that endpoint
calls `upload_prescription` here, which stores the bytes in the `prescriptions`
bucket and returns a public URL. The URL is then passed to GPT-4o Vision.

NOTE: the bucket is public in the shared setup, which means prescription images
(PHI) are world-readable by URL. That's fine for a demo but should be moved to a
private bucket with signed URLs before any real patient data flows through it.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Optional

from config import settings
from services.database import db  # reuse the same Supabase client

logger = logging.getLogger(__name__)

_EXT_BY_TYPE = {
    "image/jpeg": "jpg",
    "image/jpg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}


async def upload_prescription(
    file_bytes: bytes,
    content_type: str = "image/jpeg",
    chat_id: Optional[str] = None,
) -> str:
    """
    Upload prescription bytes to the prescriptions bucket and return a public URL.
    """
    ext = _EXT_BY_TYPE.get((content_type or "").lower(), "jpg")
    prefix = f"{chat_id}/" if chat_id else ""
    path = f"{prefix}{uuid.uuid4().hex}.{ext}"
    bucket = settings.SUPABASE_PRESCRIPTION_BUCKET
    client = db._client  # noqa: SLF001 — intentional client reuse

    def _upload():
        client.storage.from_(bucket).upload(
            path=path,
            file=file_bytes,
            file_options={"content-type": content_type, "upsert": "true"},
        )
        return client.storage.from_(bucket).get_public_url(path)

    public_url = await asyncio.to_thread(_upload)
    # Some client versions append a trailing "?" — normalise it away.
    if isinstance(public_url, str):
        public_url = public_url.rstrip("?")
    logger.info("Uploaded prescription to %s", path)
    return public_url
