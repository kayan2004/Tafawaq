"""Exam generation and session management service."""
from __future__ import annotations

import json
import pathlib
from datetime import datetime, timedelta, timezone
from typing import AsyncGenerator
from uuid import UUID

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import SessionStatus, SessionType
from app.domain.exceptions import ActiveSessionExists, AIServiceUnavailable, ExamNotFound, SessionExpired
from app.domain.models import ExamContent, ExamSession
from app.infra.llm.claude import stream_claude
from app.infra.redis_client import set_session
from app.infra.vault import AppSecrets
from app.repositories import exam_repo, message_repo

# Load curriculum and few-shot examples once at module import.
_DATA_DIR = pathlib.Path(__file__).parent.parent / "data"
_curriculum: dict = json.loads((_DATA_DIR / "curriculum.json").read_text())

_few_shot_exams: list[dict] = []
_fs_dir = _DATA_DIR / "few_shot_exams"
if _fs_dir.exists():
    for _p in sorted(_fs_dir.glob("*.json")):
        _few_shot_exams.append(json.loads(_p.read_text()))


def _build_generation_system_prompt() -> str:
    in_scope = ", ".join(_curriculum["in_scope"])
    out_of_scope = ", ".join(_curriculum["out_of_scope"])
    few_shot_block = json.dumps(_few_shot_exams, indent=2) if _few_shot_exams else "[]"

    return f"""You are an expert Lebanese GS Grade 12 Math exam generator for the official Lebanese Baccalaureate.

CURRICULUM SCOPE ({_curriculum['academic_year']}):
In-scope topics: {in_scope}
Out-of-scope (NEVER include): {out_of_scope}

INSTRUCTIONS:
- Generate a complete 20-point Lebanese GS Math mock exam with 4 exercises.
- Each exercise should cover a different in-scope topic.
- Allocate marks across exercises summing to exactly 20 points.
- Each exercise must have multiple parts (sub-questions) with individual mark allocations.
- Use LaTeX notation for all mathematical expressions (e.g. \\frac{{1}}{{2}}, \\int_0^1).
- Include an "answer_key" section alongside each exercise part — this is the official solution.
- Output ONLY a valid JSON object — no prose, no markdown fences, no explanation.

OUTPUT FORMAT (strict JSON, no fences):
{{
  "exam_content": {{
    "exercises": [
      {{
        "id": 1,
        "topic": "topic name",
        "total_marks": 5,
        "content": "exercise stem with LaTeX",
        "parts": [
          {{"part": "1", "marks": 2, "content": "part question with LaTeX"}}
        ]
      }}
    ]
  }},
  "answer_key": {{
    "exercises": [
      {{
        "id": 1,
        "parts": [
          {{"part": "1", "solution": "detailed solution with LaTeX"}}
        ]
      }}
    ]
  }}
}}

REFERENCE EXAM STRUCTURES (use as style guide — do not copy content):
{few_shot_block}"""


async def generate_exam(
    user_id: UUID,
    secrets: AppSecrets,
    db_session: AsyncSession,
    redis: Redis,
    session_type: SessionType = SessionType.mock_generated,
) -> AsyncGenerator[str, None]:
    existing = await exam_repo.get_active_session(db_session, user_id)
    if existing is not None:
        raise ActiveSessionExists(
            active_session_id=existing.id,
            expires_at=existing.expires_at,
        )

    conversation = await message_repo.create_conversation(db_session, user_id)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=3)

    placeholder_session = await exam_repo.create_session(
        session=db_session,
        user_id=user_id,
        conversation_id=conversation.id,
        session_type=session_type,
        exam_content={},
        answer_key={},
        expires_at=expires_at,
    )
    await db_session.commit()

    yield f"data: {json.dumps({'event': 'session_created', 'session_id': str(placeholder_session.id), 'expires_at': expires_at.isoformat()})}\n\n"

    system = _build_generation_system_prompt()
    messages = [{"role": "user", "content": "Generate a 20-point Lebanese GS Math mock exam."}]

    accumulated = ""
    try:
        async for chunk in stream_claude(messages, system=system, api_key=secrets.anthropic_api_key, max_tokens=8000):
            if chunk == "data: [DONE]\n\n":
                break
            yield chunk
            try:
                payload = json.loads(chunk[6:])
                if payload.get("event") == "token":
                    accumulated += payload.get("text", "")
            except (json.JSONDecodeError, IndexError):
                pass
    except AIServiceUnavailable:
        raise

    # Strip markdown fences defensively before parsing.
    clean = accumulated.strip()
    if clean.startswith("```"):
        clean = clean.split("\n", 1)[-1]
        if clean.endswith("```"):
            clean = clean[: clean.rfind("```")]

    try:
        parsed = json.loads(clean)
        exam_content_dict = parsed["exam_content"]
        answer_key_dict = parsed.get("answer_key", {})
        ExamContent.model_validate(exam_content_dict)
    except (json.JSONDecodeError, KeyError, Exception) as exc:
        raise AIServiceUnavailable(f"Model returned malformed exam JSON: {exc}") from exc

    placeholder_session.exam_content = exam_content_dict
    placeholder_session.answer_key = answer_key_dict
    await db_session.commit()

    await set_session(redis, str(placeholder_session.id), {"answer_key": answer_key_dict})

    yield f"data: {json.dumps({'event': 'exam_complete', 'exam_content': exam_content_dict})}\n\n"
    yield "data: [DONE]\n\n"


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
    now = datetime.now(timezone.utc)
    expires = row.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires < now and row.status == SessionStatus.in_progress:
        raise SessionExpired(f"Exam session {session_id} has expired.")
    return _orm_to_domain(row)


def _orm_to_domain(row) -> ExamSession:
    expires = row.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    created = row.created_at
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    return ExamSession(
        id=row.id,
        user_id=row.user_id,
        session_type=row.session_type,
        status=row.status,
        exam_content=ExamContent.model_validate(row.exam_content) if row.exam_content else ExamContent(exercises=[]),
        created_at=created,
        expires_at=expires,
    )
