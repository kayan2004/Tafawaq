"""Textbook repository — SQLAlchemy async queries against textbook_pages."""
from __future__ import annotations

from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.orm import TextbookPageORM


async def get_page_by_number(
    session: AsyncSession, page_number: int
) -> TextbookPageORM | None:
    result = await session.execute(
        select(TextbookPageORM).where(TextbookPageORM.page_number == page_number)
    )
    return result.scalar_one_or_none()


async def upsert_page(session: AsyncSession, page: TextbookPageORM) -> None:
    """INSERT ... ON CONFLICT (page_number) DO NOTHING — idempotent ingestion."""
    stmt = (
        pg_insert(TextbookPageORM)
        .values(
            id=uuid4(),
            page_number=page.page_number,
            chapter=page.chapter,
            section=page.section,
            page_type=page.page_type,
            content=page.content,
        )
        .on_conflict_do_nothing(index_elements=["page_number"])
    )
    await session.execute(stmt)
