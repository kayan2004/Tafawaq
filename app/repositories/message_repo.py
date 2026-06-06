"""Conversation and message CRUD — SQLAlchemy AsyncSession."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import MessageRole
from app.repositories.orm import ConversationORM, MessageORM


async def create_conversation(
    session: AsyncSession,
    user_id: UUID,
) -> ConversationORM:
    row = ConversationORM(user_id=user_id)
    session.add(row)
    await session.flush()
    await session.refresh(row)
    return row


async def get_conversation(
    session: AsyncSession,
    conversation_id: UUID,
) -> ConversationORM | None:
    result = await session.execute(
        select(ConversationORM).where(ConversationORM.id == conversation_id)
    )
    return result.scalar_one_or_none()


async def add_message(
    session: AsyncSession,
    conversation_id: UUID,
    role: MessageRole,
    content: str,
    guardrails_score: float | None = None,
) -> MessageORM:
    row = MessageORM(
        conversation_id=conversation_id,
        role=role,
        content=content,
        guardrails_score=guardrails_score,
    )
    session.add(row)
    await session.flush()
    await session.refresh(row)
    return row


async def get_messages(
    session: AsyncSession,
    conversation_id: UUID,
    limit: int = 20,
) -> list[MessageORM]:
    result = await session.execute(
        select(MessageORM)
        .where(MessageORM.conversation_id == conversation_id)
        .order_by(MessageORM.created_at.asc())
        .limit(limit)
    )
    return list(result.scalars())
