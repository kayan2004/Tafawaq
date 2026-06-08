"""GET /textbook/page/{page_number}."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_async_session
from app.domain.exceptions import TextbookPageNotFound
from app.domain.models import TextbookPage
from app.infra.auth import current_active_user
from app.repositories import textbook_repo
from app.repositories.orm import UserORM

router = APIRouter(prefix="/textbook", tags=["textbook"])


@router.get("/page/{page_number}", response_model=TextbookPage)
async def get_textbook_page(
    page_number: int,
    session: AsyncSession = Depends(get_async_session),
    _user: UserORM = Depends(current_active_user),
) -> TextbookPage:
    page = await textbook_repo.get_page_by_number(session, page_number)
    if page is None:
        raise TextbookPageNotFound(f"Page {page_number} not found in the textbook.")
    return TextbookPage(
        page_number=page.page_number,
        chapter=page.chapter,
        section=page.section,
        page_type=page.page_type,
        content=page.content,
    )
