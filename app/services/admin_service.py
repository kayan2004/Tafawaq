"""Admin panel orchestration — overview stats, ingestion triggers, topics, guardrails, users."""
from __future__ import annotations

import asyncio
import json
import pathlib
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import AsyncGenerator
from uuid import UUID

import asyncpg
import pgvector.asyncpg
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import GuardrailLevel
from app.domain.exceptions import AdminFileNotFound, AdminUserNotFound
from app.infra.vault import AppSecrets
from app.repositories import admin_repo, guardrail_repo
from app.services import topic_service
from ingestion import pipeline as past_exam_pipeline
from ingestion import tagger as past_exam_tagger
from ingestion import textbook_pipeline
from ingestion.chunker import chunk_pdf
from ingestion.embedder import embed_batch
from ingestion.pdf_extractor import extract_pages

_DATA_DIR = pathlib.Path(__file__).parent.parent / "data"
_curriculum: dict = json.loads((_DATA_DIR / "curriculum.json").read_text())

_PAST_EXAM_DIR = Path("Math_GS_Exams_English")


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


# ── Overview ────────────────────────────────────────────────────────────────


async def get_overview(db_session: AsyncSession) -> dict:
    total_users = await admin_repo.count_users(db_session)
    onboarded_users = await admin_repo.count_onboarded_users(db_session)
    exams_generated = await admin_repo.count_exam_sessions(db_session)
    exams_submitted = await admin_repo.count_exam_results(db_session)
    chunks_by_source_type = await admin_repo.count_chunks_by_source_type(db_session)
    topics_tracked = await admin_repo.count_topics(db_session)
    messages_total = await admin_repo.count_messages(db_session)
    since = datetime.now(timezone.utc) - timedelta(days=7)
    messages_7d = await admin_repo.count_messages(db_session, since=since)

    past_exam_files = await list_past_exam_files(db_session)
    past_exam_files_ingested = sum(1 for f in past_exam_files if f["ingested"])

    return {
        "total_users": total_users,
        "onboarded_users": onboarded_users,
        "onboarding_rate": (onboarded_users / total_users) if total_users else 0.0,
        "exams_generated": exams_generated,
        "exams_submitted": exams_submitted,
        "chunks_by_source_type": chunks_by_source_type,
        "topics_tracked": topics_tracked,
        "messages_total": messages_total,
        "messages_7d": messages_7d,
        "past_exam_files_total": len(past_exam_files),
        "past_exam_files_ingested": past_exam_files_ingested,
    }


# ── Past-exam ingestion ────────────────────────────────────────────────────────


async def list_past_exam_files(db_session: AsyncSession) -> list[dict]:
    chunk_counts = await admin_repo.count_past_exam_chunks_by_year_session(db_session)
    files: list[dict] = []
    for pdf_path in sorted(_PAST_EXAM_DIR.glob("*.pdf")):
        name = pdf_path.name
        try:
            year, session = past_exam_pipeline.filename_to_meta(name)
        except ValueError:
            files.append(
                {
                    "filename": name,
                    "year": None,
                    "session": None,
                    "ingested": False,
                    "chunk_count": 0,
                    "parse_error": True,
                }
            )
            continue
        chunk_count = chunk_counts.get((year, session), 0)
        files.append(
            {
                "filename": name,
                "year": year,
                "session": session,
                "ingested": chunk_count > 0,
                "chunk_count": chunk_count,
                "parse_error": False,
            }
        )
    return files


async def validate_past_exam_filenames(filenames: list[str]) -> None:
    """Raises AdminFileNotFound if any filename is missing on disk.

    Must be awaited by the router BEFORE constructing the StreamingResponse —
    once the SSE stream starts (200 + headers sent) errors can no longer map to 4xx.
    """
    missing = [f for f in filenames if not (_PAST_EXAM_DIR / f).is_file()]
    if missing:
        raise AdminFileNotFound(f"File(s) not found: {', '.join(missing)}")


async def stream_past_exam_ingestion(
    filenames: list[str],
    secrets: AppSecrets,
) -> AsyncGenerator[str, None]:
    # A connection opened via FastAPI's Depends(get_db_conn) is torn down by the
    # dependency's exit stack as soon as this route handler returns — i.e. before
    # this generator resumes past its first yield — leaving it closed for the
    # rest of the run. Open and own a connection here instead, scoped to the
    # generator's own lifetime, exactly like ingestion/pipeline.py:run_pipeline.
    db_url = secrets.db_url.replace("postgresql+asyncpg://", "postgresql://")
    conn = await asyncpg.connect(db_url)
    await pgvector.asyncpg.register_vector(conn)
    try:
        for filename in filenames:
            try:
                yield _sse({"event": "file_progress", "file": filename, "stage": "extract"})
                year, session = past_exam_pipeline.filename_to_meta(filename)
                pdf_bytes = await asyncio.to_thread((_PAST_EXAM_DIR / filename).read_bytes)
                pages = await asyncio.to_thread(extract_pages, pdf_bytes)

                yield _sse({"event": "file_progress", "file": filename, "stage": "chunk"})
                chunks = await asyncio.to_thread(chunk_pdf, pages, year, session)

                yield _sse({"event": "file_progress", "file": filename, "stage": "tag"})
                chunks = await asyncio.to_thread(past_exam_tagger.tag_chunks, chunks)

                yield _sse({"event": "file_progress", "file": filename, "stage": "embed"})
                chunks = await asyncio.to_thread(embed_batch, chunks, secrets.voyage_api_key)

                chunk_count = await past_exam_pipeline.insert_chunks(conn, chunks)
                await past_exam_pipeline.refresh_topic_stats(conn)

                yield _sse(
                    {
                        "event": "file_progress",
                        "file": filename,
                        "stage": "done",
                        "chunks": chunk_count,
                    }
                )
            except Exception as exc:
                yield _sse({"event": "file_failed", "file": filename, "error": str(exc)[:300]})
                continue
    finally:
        await conn.close()

    yield _sse({"event": "done"})
    yield "data: [DONE]\n\n"


# ── Textbook ingestion ──────────────────────────────────────────────────────


async def list_textbook_chapters(db_session: AsyncSession) -> list[dict]:
    return await admin_repo.list_textbook_chapter_meta(db_session)


async def stream_textbook_ingestion(
    files: list[tuple[str, bytes]],
    secrets: AppSecrets,
) -> AsyncGenerator[str, None]:
    # files are (filename, content_bytes) pairs, already read by the router before
    # the StreamingResponse was constructed — FastAPI/Starlette closes UploadFile
    # streams as soon as the route handler returns, before this generator resumes
    # past its first yield, so UploadFile objects can't be read lazily in here.
    #
    # Same reasoning as stream_past_exam_ingestion for owning the connection here
    # rather than via Depends(get_db_conn): a request-scoped dependency is torn
    # down before this generator resumes, so it must be opened in this scope.
    db_url = secrets.db_url.replace("postgresql+asyncpg://", "postgresql://")
    conn = await asyncpg.connect(db_url)
    try:
        for filename, content_bytes in files:
            tmp_path: Path | None = None
            try:
                yield _sse({"event": "file_progress", "file": filename, "stage": "parse"})
                with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as tmp:
                    tmp.write(content_bytes)
                    tmp_path = Path(tmp.name)

                pages = await asyncio.to_thread(textbook_pipeline.parse_page, tmp_path)
                if not pages:
                    yield _sse({"event": "file_failed", "file": filename, "error": "No valid pages parsed"})
                    continue

                page_count = await textbook_pipeline.insert_textbook_pages(conn, pages)

                yield _sse(
                    {
                        "event": "file_progress",
                        "file": filename,
                        "stage": "done",
                        "pages": page_count,
                    }
                )
            except Exception as exc:
                yield _sse({"event": "file_failed", "file": filename, "error": str(exc)[:300]})
                continue
            finally:
                if tmp_path is not None:
                    tmp_path.unlink(missing_ok=True)
    finally:
        await conn.close()

    yield _sse({"event": "done"})
    yield "data: [DONE]\n\n"


# ── Topics ──────────────────────────────────────────────────────────────────


async def get_topics_with_gaps(db_session: AsyncSession) -> dict:
    stats = await topic_service.get_all_topic_stats(db_session)
    covered = {s.topic for s in stats}
    gaps = [t["title"] for t in _curriculum["topics"] if t["title"] not in covered]
    return {"topics": [s.model_dump() for s in stats], "gaps": gaps}


# ── Guardrails ──────────────────────────────────────────────────────────────


async def get_guardrails_summary(db_session: AsyncSession) -> dict:
    since = datetime.now(timezone.utc) - timedelta(days=7)
    messages_7d = await admin_repo.count_messages(db_session, since=since)
    counts = await guardrail_repo.count_events_by_level(db_session, since=since)
    blocked = counts.get(GuardrailLevel.blocked, 0)
    warned = counts.get(GuardrailLevel.warned, 0)
    block_rate = (blocked / messages_7d) if messages_7d else 0.0
    return {"messages_7d": messages_7d, "blocked": blocked, "warned": warned, "block_rate": block_rate}


async def get_guardrails_messages(
    db_session: AsyncSession,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> list[dict]:
    start = date_from or (datetime.now(timezone.utc) - timedelta(days=7))
    # until=date_to (not a "now" default): get_recent_events treats until=None as
    # "no upper bound", which avoids a host/container clock-skew race that can
    # otherwise exclude a row inserted moments ago (fixed mid-Task-6 after the
    # same bug appeared in Tasks 2 and 5's tests; see SESSION_LOG.md).
    events = await guardrail_repo.get_recent_events(db_session, since=start, until=date_to)
    return [
        {
            "ts": event.created_at.isoformat(),
            "text": event.text_preview,
            "score": event.score,
            "level": event.level.value,
            "reason": event.reason,
        }
        for event in events
    ]


# ── Users ───────────────────────────────────────────────────────────────────


async def list_users(db_session: AsyncSession) -> list[dict]:
    return await admin_repo.list_users_with_aggregates(db_session)


async def deactivate_user(db_session: AsyncSession, user_id: UUID) -> None:
    found = await admin_repo.deactivate_user(db_session, user_id)
    if not found:
        raise AdminUserNotFound(f"User {user_id} not found.")
