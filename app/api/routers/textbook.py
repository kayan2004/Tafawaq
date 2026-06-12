"""Textbook endpoints: PDF streaming, TOC listing, page fetch."""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_async_session, get_secrets
from app.domain.exceptions import TextbookPageNotFound, TextbookPdfMissing
from app.domain.models import TextbookPage, TextbookPageMeta
from app.infra.auth import current_active_user
from app.infra.minio_client import TEXTBOOKS_BUCKET, get_minio_client, get_pdf_bytes
from app.infra.vault import AppSecrets
from app.repositories import textbook_repo
from app.repositories.orm import UserORM

router = APIRouter(prefix="/textbook", tags=["textbook"])


@router.get("/pdf/{filename}")
async def get_textbook_pdf(
    filename: str,
    secrets: AppSecrets = Depends(get_secrets),
    _user: UserORM = Depends(current_active_user),
) -> Response:
    client = get_minio_client(secrets)
    try:
        data = await asyncio.to_thread(get_pdf_bytes, client, TEXTBOOKS_BUCKET, filename)
    except Exception:
        raise TextbookPdfMissing(f"PDF '{filename}' not found in object storage.")
    return Response(content=data, media_type="application/pdf")


@router.get("/pages", response_model=list[TextbookPageMeta])
async def list_textbook_pages(
    session: AsyncSession = Depends(get_async_session),
    _user: UserORM = Depends(current_active_user),
) -> list[TextbookPageMeta]:
    return await textbook_repo.list_page_metadata(session)


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
