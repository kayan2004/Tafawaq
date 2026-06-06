"""Guardrails: off-topic classification via NeMo Guardrails service + Redis counter."""
from __future__ import annotations

import os

import httpx
from redis.asyncio import Redis

from app.domain.exceptions import AIServiceUnavailable
from app.infra.redis_client import (
    get_guardrails_counter,
    increment_guardrails_counter,
    set_guardrails_counter,
)

_GUARDRAILS_URL = os.environ.get("GUARDRAILS_URL", "http://guardrails:8100")
_MIN_WORDS_TO_CLASSIFY = 10


async def classify_message(text: str) -> bool:
    """Return True if the message is off-topic for Lebanese GS Math exam prep.

    Short messages (< 10 words) are always treated as on-topic to avoid
    false positives on greetings and single-word queries.
    Calls the NeMo Guardrails service; maps HTTP/network errors to AIServiceUnavailable.
    """
    if len(text.split()) < _MIN_WORDS_TO_CLASSIFY:
        return False

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{_GUARDRAILS_URL}/check",
                json={"message": text},
            )
            response.raise_for_status()
            return response.json()["off_topic"]
    except httpx.HTTPStatusError as exc:
        raise AIServiceUnavailable(f"Guardrails service returned {exc.response.status_code}") from exc
    except httpx.RequestError as exc:
        raise AIServiceUnavailable(f"Guardrails service unreachable: {exc}") from exc


async def get_counter(redis: Redis, conversation_id: str) -> int:
    return await get_guardrails_counter(redis, conversation_id)


async def increment_counter(redis: Redis, conversation_id: str) -> int:
    return await increment_guardrails_counter(redis, conversation_id)


async def reset_counter(redis: Redis, conversation_id: str) -> None:
    await set_guardrails_counter(redis, conversation_id, 0)


def get_guardrail_tier(counter: int) -> str:
    if counter <= 1:
        return "normal"
    if counter == 2:
        return "warning"
    return "block"
