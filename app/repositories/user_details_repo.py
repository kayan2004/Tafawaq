"""User details repository — SQL only, no HTTP errors, no business logic."""
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import Branch, Language
from app.domain.models import UserDetails
from app.repositories.orm import UserDetailsORM


async def get_user_details(session: AsyncSession, user_id: UUID) -> UserDetails | None:
    result = await session.execute(
        select(UserDetailsORM).where(UserDetailsORM.user_id == user_id)
    )
    row = result.scalar_one_or_none()
    if row is None:
        return None
    return _to_domain(row)


async def upsert_user_details(
    session: AsyncSession,
    user_id: UUID,
    language: Language,
    grade: int,
    branch: Branch | None,
) -> UserDetails:
    result = await session.execute(
        select(UserDetailsORM).where(UserDetailsORM.user_id == user_id)
    )
    row = result.scalar_one_or_none()
    if row is None:
        row = UserDetailsORM(user_id=user_id, language=language, grade=grade, branch=branch)
        session.add(row)
    else:
        row.language = language
        row.grade = grade
        row.branch = branch
    await session.commit()
    await session.refresh(row)
    return _to_domain(row)


def _to_domain(row: UserDetailsORM) -> UserDetails:
    return UserDetails(
        user_id=row.user_id,
        language=row.language,
        grade=row.grade,
        branch=row.branch,
        updated_at=row.updated_at,
    )
