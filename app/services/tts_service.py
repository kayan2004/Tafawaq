"""TTS service: cache-first (MinIO tts-cache bucket) synthesis via ElevenLabs."""
from __future__ import annotations

import asyncio
import hashlib

from app.infra import tts as tts_infra
from app.infra.minio_client import get_minio_client, get_pdf_bytes, upload_pdf
from app.infra.vault import AppSecrets

_TTS_BUCKET = "tts-cache"


def _cache_key(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest() + ".mp3"


def _try_get(client, key: str) -> bytes | None:
    try:
        return get_pdf_bytes(client, _TTS_BUCKET, key)
    except Exception:
        return None


async def get_or_synthesize(text: str, secrets: AppSecrets) -> bytes:
    """Return mp3 bytes for *text*, using MinIO as a cache.

    Cache miss → ElevenLabs → store in MinIO → return bytes.
    MinIO write failures are silently swallowed (non-fatal).
    """
    client = get_minio_client(secrets)
    key = _cache_key(text)

    cached = await asyncio.to_thread(_try_get, client, key)
    if cached is not None:
        return cached

    audio = await tts_infra.synthesize(text, secrets.elevenlabs_api_key)

    try:
        await asyncio.to_thread(upload_pdf, client, _TTS_BUCKET, key, audio)
    except Exception:
        pass

    return audio
