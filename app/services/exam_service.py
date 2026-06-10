"""Exam generation and session management service."""
from __future__ import annotations

import asyncio
import json
import pathlib
from datetime import datetime, timezone
from typing import AsyncGenerator
from uuid import UUID

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import SessionType
from app.domain.exceptions import ExamNotFound
from app.domain.models import AnswerKey, ExamContent, ExamSession
from app.infra.llm.claude import call_claude
from app.infra.redis_client import set_session
from app.infra.vault import AppSecrets
from app.repositories import exam_repo, message_repo

from prompts.exam_generation import build_generation_system_prompt as _build_gen_prompt_fn, parse_generation_response

# Load data files once at module import.
_DATA_DIR = pathlib.Path(__file__).parent.parent / "data"
_curriculum: dict = json.loads((_DATA_DIR / "curriculum.json").read_text())
_exam_config: dict = json.loads((_DATA_DIR / "exam_config.json").read_text())
_exam_analysis: dict = json.loads((_DATA_DIR / "exam_analysis.json").read_text())

_few_shot_exams: list[str] = []
_fs_exam = _DATA_DIR / "2021_regular_exam.md"
if _fs_exam.exists():
    _few_shot_exams.append(_fs_exam.read_text())


def _build_generation_system_prompt() -> str:
    return _build_gen_prompt_fn(_curriculum, _exam_analysis, _exam_config, _few_shot_exams)


async def generate_exam(
    user_id: UUID,
    secrets: AppSecrets,
    db_session: AsyncSession,
    redis: Redis,
    session_type: SessionType = SessionType.mock_generated,
) -> AsyncGenerator[str, None]:
    await exam_repo.archive_active_sessions(db_session, user_id)

    conversation = await message_repo.create_conversation(db_session, user_id)

    placeholder_session = await exam_repo.create_session(
        session=db_session,
        user_id=user_id,
        conversation_id=conversation.id,
        session_type=session_type,
        exam_content={},
        answer_key={},
    )
    await db_session.commit()

    yield f"data: {json.dumps({'event': 'session_created', 'session_id': str(placeholder_session.id)})}\n\n"

    system = _build_generation_system_prompt()
    messages = [{"role": "user", "content": "Generate a 20-point Lebanese GS Math mock exam."}]

    try:
        raw = await asyncio.to_thread(
            call_claude, messages, system=system, api_key=secrets.anthropic_api_key, max_tokens=16000
        )
        parsed = parse_generation_response(raw)
        exam_content = ExamContent.model_validate(parsed["exam"])
        answer_key = AnswerKey.model_validate(parsed["answer_key"])
    except Exception as exc:
        yield f"data: {json.dumps({'event': 'error', 'message': str(exc) or 'AI service error'})}\n\n"
        return

    if not exam_content.exercises:
        yield f"data: {json.dumps({'event': 'error', 'message': 'Model returned an empty exam. Please try again.'})}\n\n"
        return

    placeholder_session.exam_content = exam_content.model_dump()
    placeholder_session.answer_key = answer_key.model_dump()
    await db_session.commit()

    await set_session(redis, str(placeholder_session.id), {"answer_key": answer_key.model_dump()})

    yield f"data: {json.dumps({'event': 'exam_complete', 'exam_content': exam_content.model_dump()})}\n\n"
    yield "data: [DONE]\n\n"


async def list_sessions(
    user_id: UUID,
    db_session: AsyncSession,
) -> list[ExamSession]:
    rows = await exam_repo.list_sessions(db_session, user_id)
    return [_orm_to_domain(row) for row in rows if row.exam_content]


async def get_active_session(
    user_id: UUID,
    db_session: AsyncSession,
) -> ExamSession:
    row = await exam_repo.get_active_session(db_session, user_id)
    if row is None:
        raise ExamNotFound("No active exam session found.")
    return _orm_to_domain(row)


async def get_session_by_id(
    session_id: UUID,
    user_id: UUID,
    db_session: AsyncSession,
) -> ExamSession:
    row = await exam_repo.get_session(db_session, session_id)
    if row is None or row.user_id != user_id:
        raise ExamNotFound(f"Exam session {session_id} not found.")
    return _orm_to_domain(row)


def _orm_to_domain(row) -> ExamSession:
    created = row.created_at
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    return ExamSession(
        id=row.id,
        user_id=row.user_id,
        session_type=row.session_type,
        status=row.status,
        exam_content=ExamContent.model_validate(row.exam_content or {}),
        created_at=created,
    )
