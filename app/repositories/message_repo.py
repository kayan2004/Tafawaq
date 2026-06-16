"""Conversation and message CRUD — SQLAlchemy AsyncSession."""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import MessageRole
from app.repositories.orm import ConversationORM, MessageORM


async def list_conversations(
    session: AsyncSession,
    user_id: UUID,
) -> list[ConversationORM]:
    """Return all named chat conversations for a user, newest activity first.

    Filters subject IS NOT NULL to exclude anonymous exam-session conversations.
    """
    result = await session.execute(
        select(ConversationORM)
        .where(ConversationORM.user_id == user_id)
        .where(ConversationORM.subject.isnot(None))
        .order_by(
            ConversationORM.last_message_at.desc().nullslast(),
            ConversationORM.created_at.desc(),
        )
    )
    return list(result.scalars())


async def get_or_create_conversation(
    session: AsyncSession,
    user_id: UUID,
    subject: str = "math_gs12",
) -> ConversationORM:
    """Return the most recent conversation for (user_id, subject), creating one if absent.

    The uniqueness constraint was dropped in migration 0007; this now returns
    the newest matching row rather than asserting exactly one exists.
    """
    result = await session.execute(
        select(ConversationORM)
        .where(ConversationORM.user_id == user_id)
        .where(ConversationORM.subject == subject)
        .order_by(ConversationORM.created_at.desc())
        .limit(1)
    )
    row = result.scalar_one_or_none()
    if row is not None:
        return row
    row = ConversationORM(user_id=user_id, subject=subject)
    session.add(row)
    await session.flush()
    await session.refresh(row)
    return row


async def create_named_conversation(
    session: AsyncSession,
    user_id: UUID,
    subject: str,
    title: str | None = None,
) -> ConversationORM:
    """Create a new named chat conversation."""
    row = ConversationORM(user_id=user_id, subject=subject, title=title)
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


async def get_conversation_for_user(
    session: AsyncSession,
    conversation_id: UUID,
    user_id: UUID,
) -> ConversationORM | None:
    """Return the conversation only if it belongs to the given user."""
    result = await session.execute(
        select(ConversationORM)
        .where(ConversationORM.id == conversation_id)
        .where(ConversationORM.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def rename_conversation(
    session: AsyncSession,
    conversation_id: UUID,
    title: str | None,
) -> None:
    await session.execute(
        update(ConversationORM)
        .where(ConversationORM.id == conversation_id)
        .values(title=title)
    )
    await session.flush()


async def clear_conversation(
    session: AsyncSession,
    conversation_id: UUID,
) -> UUID | None:
    """Set cleared_at = now() on the conversation.

    Returns the conversation ID so the caller can reset derived state (e.g. Redis
    guardrail counter). Returns None if the conversation doesn't exist.
    """
    result = await session.execute(
        select(ConversationORM).where(ConversationORM.id == conversation_id)
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
    await session.execute(
        update(ConversationORM)
        .where(ConversationORM.id == conversation_id)
        .values(last_message_at=datetime.now(timezone.utc))
    )
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
