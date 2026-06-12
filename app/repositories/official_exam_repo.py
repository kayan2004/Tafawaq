"""Official exam CRUD — SQLAlchemy AsyncSession."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.orm import OfficialExamORM


async def list_all(session: AsyncSession) -> list[OfficialExamORM]:
    result = await session.execute(
        select(OfficialExamORM).order_by(
            OfficialExamORM.year.desc(), OfficialExamORM.session_label
        )
    )
    return list(result.scalars())


async def get_by_id(session: AsyncSession, exam_id: UUID) -> OfficialExamORM | None:
    result = await session.execute(
        select(OfficialExamORM).where(OfficialExamORM.id == exam_id)
    )
    return result.scalar_one_or_none()
