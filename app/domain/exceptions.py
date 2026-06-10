"""Domain exception hierarchy.

All exceptions are raised by services and repositories only.
HTTP status mapping lives exclusively in app/api/exceptions.py.
"""
from uuid import UUID
from datetime import datetime


class LebaneseCoachError(Exception):
    """Base exception for all domain errors."""


# ── 404 Not Found ────────────────────────────────────────────────────────────

class ExamNotFound(LebaneseCoachError):
    """Exam session does not exist or does not belong to the requesting user."""


class AnswerKeyNotFound(LebaneseCoachError):
    """Answer key for the given year/session/exercise not found in the vector store."""


class TopicNotFound(LebaneseCoachError):
    """Topic does not exist in topic_stats."""


class TextbookPageNotFound(LebaneseCoachError):
    """Textbook page does not exist in the textbook_pages table."""


# ── 409 Conflict ─────────────────────────────────────────────────────────────

class ActiveSessionExists(LebaneseCoachError):
    """Student already has an in-progress session (FR-024).

    Attributes:
        active_session_id: UUID of the blocking session.
        expires_at: When the blocking session expires.
    """
    def __init__(self, active_session_id: UUID, expires_at: datetime) -> None:
        self.active_session_id = active_session_id
        self.expires_at = expires_at
        super().__init__(
            f"Active session {active_session_id} exists until {expires_at.isoformat()}"
        )


# ── 410 Gone ─────────────────────────────────────────────────────────────────

class SessionExpired(LebaneseCoachError):
    """Exam session TTL has elapsed."""


# ── 422 Unprocessable ────────────────────────────────────────────────────────

class InvalidAnswerSubmission(LebaneseCoachError):
    """Submitted answers reference exercise IDs not present in the exam."""


# ── 502 Bad Gateway ──────────────────────────────────────────────────────────

class EvaluatorResponseError(LebaneseCoachError):
    """Evaluator returned a response that could not be parsed into a valid result."""


# ── 503 Service Unavailable ──────────────────────────────────────────────────

class AIServiceUnavailable(LebaneseCoachError):
    """Claude API unreachable or returned a non-retryable error (FR-026)."""


class EmbeddingServiceUnavailable(LebaneseCoachError):
    """Voyage AI API unreachable or returned a non-retryable error."""


class VaultUnavailable(LebaneseCoachError):
    """HashiCorp Vault unreachable at application startup (Constitution Principle II)."""


# ── Chat / Guardrails (handled in chat flow, not as HTTP errors) ─────────────

class OffTopicBlocked(LebaneseCoachError):
    """Student has exceeded off-topic message threshold; soft-block triggered."""
