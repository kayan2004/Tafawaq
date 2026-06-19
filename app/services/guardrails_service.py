"""Guardrails: multi-category classification via the NeMo Guardrails sidecar +
Redis counter (off-topic tier) + structured event logging for the admin audit log.
"""
from __future__ import annotations

import asyncio
import hashlib
import os
from dataclasses import dataclass
from uuid import UUID

import httpx
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import GuardrailCategory, GuardrailDirection, GuardrailLevel, GuardrailSource
from app.domain.exceptions import AIServiceUnavailable
from app.infra import pii_redaction
from app.infra.redis_client import (
    get_guardrails_counter,
    increment_guardrails_counter,
    set_guardrails_counter,
)
from app.repositories import guardrail_repo

_GUARDRAILS_URL = os.environ.get("GUARDRAILS_URL", "http://guardrails:8100")

_VALID_CATEGORIES = {c.value for c in GuardrailCategory}


@dataclass
class InputVerdict:
    category: GuardrailCategory | None
    score: float
    reason: str


@dataclass
class OutputVerdict:
    flagged: bool
    score: float
    reason: str


async def _call_sidecar(endpoint: str, text: str) -> dict:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(f"{_GUARDRAILS_URL}{endpoint}", json={"message": text})
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as exc:
        raise AIServiceUnavailable(f"Guardrails service returned {exc.response.status_code}") from exc
    except httpx.RequestError as exc:
        raise AIServiceUnavailable(f"Guardrails service unreachable: {exc}") from exc


async def classify_input(text: str) -> InputVerdict:
    """Classify a chat message or exam-generation brief.

    No length short-circuit: a short message can still be a complete injection
    attempt ("ignore all instructions" is 3 words), so skipping classification
    below a word count would defeat injection detection.
    """
    data = await _call_sidecar("/check", text)
    category_raw = data.get("category")
    category = GuardrailCategory(category_raw) if category_raw in _VALID_CATEGORIES else None
    return InputVerdict(
        category=category,
        score=float(data.get("score", 0.0)),
        reason=str(data.get("reason", "")),
    )


async def classify_output(text: str) -> OutputVerdict:
    """Classify generated content (chat reply or exam exercise) for safety only."""
    data = await _call_sidecar("/check-output", text)
    return OutputVerdict(
        flagged=bool(data.get("flagged", False)),
        score=float(data.get("score", 0.0)),
        reason=str(data.get("reason", "")),
    )


async def log_event(
    session: AsyncSession,
    *,
    user_id: UUID,
    conversation_id: UUID | None,
    source: GuardrailSource,
    direction: GuardrailDirection,
    category: GuardrailCategory | None,
    level: GuardrailLevel,
    score: float,
    reason: str,
    text: str,
) -> None:
    """Single choke point for guardrail_events writes — hashes the original text,
    truncates and redacts the preview so no caller can accidentally store raw PII."""
    text_hash = hashlib.sha256(text.encode()).hexdigest()
    preview = pii_redaction.redact(text[:100])
    await guardrail_repo.insert_event(
        session,
        user_id=user_id,
        conversation_id=conversation_id,
        source=source,
        direction=direction,
        category=category,
        level=level,
        score=score,
        reason=reason,
        text_hash=text_hash,
        text_preview=preview,
    )


# Holds strong references to background tasks so GC cannot collect them mid-run
# (mirrors app/services/exam_service.py's _bg_tasks pattern).
_bg_tasks: set[asyncio.Task] = set()
_bg_engine = None
_bg_maker = None


def _get_bg_maker(db_url: str):
    global _bg_engine, _bg_maker
    if _bg_maker is None:
        from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
        _bg_engine = create_async_engine(db_url, echo=False)
        _bg_maker = async_sessionmaker(_bg_engine, expire_on_commit=False)
    return _bg_maker


async def _audit_output(db_url: str, text: str, user_id: UUID, conversation_id: UUID) -> None:
    try:
        verdict = await classify_output(text)
    except AIServiceUnavailable:
        return  # best-effort audit — the sidecar being down must not surface anywhere
    if not verdict.flagged:
        return
    maker = _get_bg_maker(db_url)
    async with maker() as session:
        await log_event(
            session,
            user_id=user_id,
            conversation_id=conversation_id,
            source=GuardrailSource.chat,
            direction=GuardrailDirection.output,
            category=None,
            level=GuardrailLevel.warned,
            score=verdict.score,
            reason=verdict.reason,
            text=text,
        )
        await session.commit()


def audit_output_async(db_url: str, text: str, user_id: UUID, conversation_id: UUID) -> None:
    """Fire-and-forget: classify the assistant's full response and log a warned
    event if flagged. Never blocks the caller, never raises into it."""
    task = asyncio.create_task(_audit_output(db_url, text, user_id, conversation_id))
    _bg_tasks.add(task)
    task.add_done_callback(_bg_tasks.discard)


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
