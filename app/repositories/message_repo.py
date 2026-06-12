"""Conversation and message CRUD — SQLAlchemy AsyncSession."""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import MessageRole
from app.repositories.orm import ConversationORM, MessageORM


async def get_or_create_conversation(
    session: AsyncSession,
    user_id: UUID,
    subject: str = "math_gs12",
) -> ConversationORM:
    """Return the existing conversation for (user_id, subject), creating it if absent."""
    result = await session.execute(
        select(ConversationORM)
        .where(ConversationORM.user_id == user_id)
        .where(ConversationORM.subject == subject)
    )
    row = result.scalar_one_or_none()
    if row is not None:
        return row
    row = ConversationORM(user_id=user_id, subject=subject)
    session.add(row)
    await session.flush()
    await session.refresh(row)
    return row


async def create_conversation(
    session: AsyncSession,
    user_id: UUID,
) -> ConversationORM:
    """Create a new anonymous conversation (subject=NULL). Used by exam sessions."""
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


async def clear_conversation(
    session: AsyncSession,
    user_id: UUID,
    subject: str = "math_gs12",
) -> UUID | None:
    """Set cleared_at = now() on the (user_id, subject) conversation.

    Returns the conversation ID so the caller can reset derived state (e.g. Redis
    guardrail counter). Returns None if no such conversation exists yet.
    """
    result = await session.execute(
        select(ConversationORM)
        .where(ConversationORM.user_id == user_id)
        .where(ConversationORM.subject == subject)
    )
    row = result.scalar_one_or_none()
    if row is None:
        return None
    row.cleared_at = datetime.now(timezone.utc)
    await session.flush()
    return row.id


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
    """Return up to `limit` messages, excluding any sent before cleared_at."""
    conv_result = await session.execute(
        select(ConversationORM).where(ConversationORM.id == conversation_id)
    )
    conv = conv_result.scalar_one_or_none()

    query = select(MessageORM).where(MessageORM.conversation_id == conversation_id)
    if conv is not None and conv.cleared_at is not None:
        query = query.where(MessageORM.created_at > conv.cleared_at)

    result = await session.execute(
        query.order_by(MessageORM.created_at.asc()).limit(limit)
    )
    return list(result.scalars())
