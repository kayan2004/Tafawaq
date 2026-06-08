"""Map domain exceptions to HTTP responses.

All exception handlers live here — never in services or repositories.
Users MUST never see stack traces (Constitution Principle IV).
"""
from fastapi import Request
from fastapi.responses import JSONResponse

from app.domain.exceptions import (
    ActiveSessionExists,
    AIServiceUnavailable,
    AnswerKeyNotFound,
    EmbeddingServiceUnavailable,
    ExamNotFound,
    InvalidAnswerSubmission,
    LebaneseCoachError,
    SessionExpired,
    TextbookPageNotFound,
    TopicNotFound,
)
from app.domain.models import ErrorResponse
from app.main import app


def _error(request: Request, status: int, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content=ErrorResponse(
            error=message,
            request_id=request.state.request_id,
        ).model_dump(),
    )


@app.exception_handler(ExamNotFound)
@app.exception_handler(AnswerKeyNotFound)
@app.exception_handler(TopicNotFound)
@app.exception_handler(TextbookPageNotFound)
async def not_found_handler(request: Request, exc: LebaneseCoachError) -> JSONResponse:
    return _error(request, 404, str(exc) or "Resource not found.")


@app.exception_handler(ActiveSessionExists)
async def active_session_handler(request: Request, exc: ActiveSessionExists) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content={
            "error": "You already have an active exam session. Submit or wait for it to expire.",
            "request_id": request.state.request_id,
            "active_session_id": str(exc.active_session_id),
            "expires_at": exc.expires_at.isoformat(),
        },
    )


@app.exception_handler(SessionExpired)
async def session_expired_handler(request: Request, exc: SessionExpired) -> JSONResponse:
    return _error(request, 410, "Exam session has expired.")


@app.exception_handler(InvalidAnswerSubmission)
async def invalid_submission_handler(request: Request, exc: InvalidAnswerSubmission) -> JSONResponse:
    return _error(request, 422, str(exc) or "Invalid answer submission.")


@app.exception_handler(AIServiceUnavailable)
@app.exception_handler(EmbeddingServiceUnavailable)
async def service_unavailable_handler(request: Request, exc: LebaneseCoachError) -> JSONResponse:
    return _error(request, 503, "Service temporarily unavailable. Please retry.")


@app.exception_handler(Exception)
async def catchall_handler(request: Request, exc: Exception) -> JSONResponse:
    # Catch-all: never leak stack traces to the client.
    return _error(request, 500, "An unexpected error occurred. Please try again.")
