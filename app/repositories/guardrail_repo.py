"""Guardrail event audit log — SQL only, no HTTP errors, no redaction logic
(redaction happens one layer up, in app.services.guardrails_service.log_event)."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import GuardrailCategory, GuardrailDirection, GuardrailLevel, GuardrailSource
from app.repositories.orm import GuardrailEventORM


async def insert_event(
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
    text_hash: str,
    text_preview: str,
) -> GuardrailEventORM:
    row = GuardrailEventORM(
        user_id=user_id,
        conversation_id=conversation_id,
        source=source,
        direction=direction,
        category=category,
        level=level,
        score=score,
        reason=reason,
        text_hash=text_hash,
        text_preview=text_preview,
    )
    session.add(row)
    await session.flush()
    await session.refresh(row)
    return row


async def count_events_by_level(session: AsyncSession, since: datetime) -> dict[GuardrailLevel, int]:
    result = await session.execute(
        select(GuardrailEventORM.level, func.count())
        .where(GuardrailEventORM.created_at >= since)
        .group_by(GuardrailEventORM.level)
    )
    return {level: count for level, count in result.all()}


async def get_recent_events(
    session: AsyncSession, since: datetime, until: datetime
) -> list[GuardrailEventORM]:
    result = await session.execute(
        select(GuardrailEventORM)
        .where(GuardrailEventORM.created_at >= since)
        .where(GuardrailEventORM.created_at <= until)
        .order_by(GuardrailEventORM.created_at.desc())
    )
    return list(result.scalars())
