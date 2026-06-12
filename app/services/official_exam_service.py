"""Official exam service — list, retrieve, spawn student session."""
from __future__ import annotations

from datetime import timezone
from uuid import UUID

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import SessionType
from app.domain.exceptions import OfficialExamNotFound, OfficialExamPdfMissing
from app.domain.models import ExamContent, OfficialExam
from app.infra.redis_client import set_session
from app.repositories import exam_repo, message_repo, official_exam_repo


async def list_official_exams(db: AsyncSession) -> list[OfficialExam]:
    rows = await official_exam_repo.list_all(db)
    return [_orm_to_domain(row) for row in rows]


async def spawn_session(
    db: AsyncSession,
    redis: Redis,
    exam_id: UUID,
    user_id: UUID,
) -> tuple[str, dict]:
    """Create an exam_session for the user from the official exam.

    Returns (session_id, exam_content_dict).
    """
    row = await official_exam_repo.get_by_id(db, exam_id)
    if row is None:
        raise OfficialExamNotFound(f"Official exam {exam_id} not found.")

    conversation = await message_repo.create_conversation(db, user_id)
    session = await exam_repo.create_session(
        session=db,
        user_id=user_id,
        conversation_id=conversation.id,
        session_type=SessionType.real_past_exam,
        exam_content=row.exam_content,
        answer_key=row.answer_key,
    )
    await db.commit()
    await set_session(redis, str(session.id), {"answer_key": row.answer_key})
    return str(session.id), row.exam_content


async def get_pdf_key(db: AsyncSession, exam_id: UUID) -> str:
    row = await official_exam_repo.get_by_id(db, exam_id)
    if row is None:
        raise OfficialExamNotFound(f"Official exam {exam_id} not found.")
    if not row.pdf_key:
        raise OfficialExamPdfMissing(f"Official exam {exam_id} has no PDF stored.")
    return row.pdf_key


def _orm_to_domain(row) -> OfficialExam:
    created = row.created_at
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    return OfficialExam(
        id=row.id,
        year=row.year,
        session_label=row.session_label,
        exam_content=ExamContent.model_validate(row.exam_content or {"exercises": []}),
        created_at=created,
    )
