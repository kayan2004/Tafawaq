from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import GuardrailCategory, GuardrailDirection, GuardrailLevel, GuardrailSource
from app.repositories import guardrail_repo
from app.repositories.orm import GuardrailEventORM, UserORM
from app.services import admin_service


async def _make_user(db_session: AsyncSession) -> UserORM:
    user = UserORM(email=f"test-{uuid.uuid4()}@example.com", hashed_password="not-a-real-hash")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.mark.asyncio
async def test_get_guardrails_summary_and_messages_reflect_real_events(db_session: AsyncSession):
    # get_guardrails_summary/get_guardrails_messages are global admin aggregates
    # (no per-user filter, by design — it's a site-wide dashboard) running against
    # a shared dev DB, so this test measures the DELTA its own two inserts cause
    # rather than asserting absolute counts, which would be flaky if any other
    # guardrail_events rows already exist within the 7-day window.
    user = await _make_user(db_session)
    try:
        since = datetime.now(timezone.utc) - timedelta(days=7)
        before_counts = await guardrail_repo.count_events_by_level(db_session, since=since)
        before_blocked = before_counts.get(GuardrailLevel.blocked, 0)
        before_warned = before_counts.get(GuardrailLevel.warned, 0)

        await guardrail_repo.insert_event(
            db_session,
            user_id=user.id,
            conversation_id=None,
            source=GuardrailSource.chat,
            direction=GuardrailDirection.input,
            category=GuardrailCategory.prompt_injection,
            level=GuardrailLevel.blocked,
            score=0.9,
            reason="ignore instructions",
            text_hash="abc",
            text_preview="ignore instructions",
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
            text_hash="def",
            text_preview="basketball",
        )
        await db_session.commit()

        summary = await admin_service.get_guardrails_summary(db_session)
        assert summary["blocked"] == before_blocked + 1
        assert summary["warned"] == before_warned + 1
        assert 0.0 <= summary["block_rate"] <= 1.0

        messages = await admin_service.get_guardrails_messages(db_session)
        previews = {m["text"] for m in messages}
        assert "ignore instructions" in previews
        assert "basketball" in previews
        match = next(m for m in messages if m["text"] == "ignore instructions")
        assert {"ts", "text", "score", "level", "reason"} <= match.keys()
        assert match["level"] == "blocked"
    finally:
        await db_session.execute(delete(GuardrailEventORM).where(GuardrailEventORM.user_id == user.id))
        await db_session.execute(delete(UserORM).where(UserORM.id == user.id))
        await db_session.commit()
