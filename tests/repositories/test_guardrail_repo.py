from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import GuardrailCategory, GuardrailDirection, GuardrailLevel, GuardrailSource
from app.repositories import guardrail_repo
from app.repositories.orm import GuardrailEventORM, UserORM


async def _make_user(db_session: AsyncSession) -> UserORM:
    user = UserORM(email=f"test-{uuid.uuid4()}@example.com", hashed_password="not-a-real-hash")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.mark.asyncio
async def test_insert_and_count_and_list_events(db_session: AsyncSession):
    # count_events_by_level/get_recent_events are global queries (no user filter
    # by design — admin_service's aggregates run against all traffic), so this
    # test measures the delta its own two inserts cause, robust to any other
    # guardrail_events rows already present in the shared dev DB.
    user = await _make_user(db_session)
    try:
        since = datetime.now(timezone.utc) - timedelta(days=1)
        before_counts = await guardrail_repo.count_events_by_level(db_session, since=since)
        before_blocked = before_counts.get(GuardrailLevel.blocked, 0)
        before_warned = before_counts.get(GuardrailLevel.warned, 0)
        before_events = await guardrail_repo.get_recent_events(
            db_session, since=since
        )
        before_ids = {e.id for e in before_events}

        await guardrail_repo.insert_event(
            db_session,
            user_id=user.id,
            conversation_id=None,
            source=GuardrailSource.chat,
            direction=GuardrailDirection.input,
            category=GuardrailCategory.prompt_injection,
            level=GuardrailLevel.blocked,
            score=0.95,
            reason="ignore instructions",
            text_hash="abc123",
            text_preview="ignore all instructions",
        )
        await guardrail_repo.insert_event(
            db_session,
            user_id=user.id,
            conversation_id=None,
            source=GuardrailSource.chat,
            direction=GuardrailDirection.input,
            category=GuardrailCategory.off_topic,
            level=GuardrailLevel.warned,
            score=0.6,
            reason="basketball",
            text_hash="def456",
            text_preview="tell me about basketball",
        )
        await db_session.commit()

        counts = await guardrail_repo.count_events_by_level(db_session, since=since)
        assert counts[GuardrailLevel.blocked] == before_blocked + 1
        assert counts[GuardrailLevel.warned] == before_warned + 1

        events = await guardrail_repo.get_recent_events(
            db_session, since=since
        )
        new_events = [e for e in events if e.id not in before_ids]
        assert len(new_events) == 2
        assert events[0].created_at >= events[1].created_at
    finally:
        await db_session.execute(delete(GuardrailEventORM).where(GuardrailEventORM.user_id == user.id))
        await db_session.execute(delete(UserORM).where(UserORM.id == user.id))
        await db_session.commit()
