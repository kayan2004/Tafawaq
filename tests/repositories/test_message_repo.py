from __future__ import annotations

import uuid

import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import MessageRole
from app.repositories import message_repo
from app.repositories.orm import ConversationORM, MessageORM, UserORM


async def _make_user(db_session: AsyncSession) -> UserORM:
    user = UserORM(
        email=f"test-{uuid.uuid4()}@example.com",
        hashed_password="not-a-real-hash",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.mark.asyncio
async def test_get_messages_returns_most_recent_messages_not_oldest(db_session: AsyncSession):
    user = await _make_user(db_session)
    conversation = await message_repo.create_conversation(db_session, user.id)
    await db_session.commit()

    total = 25
    limit = 20
    try:
        for i in range(total):
            await message_repo.add_message(db_session, conversation.id, MessageRole.user, f"msg-{i}")
            await db_session.commit()

        history = await message_repo.get_messages(db_session, conversation.id, limit=limit)

        contents = [m.content for m in history]
        expected = [f"msg-{i}" for i in range(total - limit, total)]
        assert contents == expected
    finally:
        await db_session.execute(delete(MessageORM).where(MessageORM.conversation_id == conversation.id))
        await db_session.execute(delete(ConversationORM).where(ConversationORM.id == conversation.id))
        await db_session.execute(delete(UserORM).where(UserORM.id == user.id))
        await db_session.commit()
