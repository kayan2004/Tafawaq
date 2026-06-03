# Data Model: Lebanese Math Coach

**Source of truth**: `DECISIONS.md` §4 defines the full schema. This document refines that schema
with: (1) ORM vs. domain model separation, (2) state machine for `exam_sessions`, (3) three
clarification-driven additions (FR-024, FR-025, FR-026), and (4) notes on layer boundaries.

---

## ORM Models (`repositories/` — never cross into services/ or api/)

All ORM models inherit from `Base = DeclarativeBase()`. They live in `repositories/orm.py`.

### users

```python
class UserORM(Base):
    __tablename__ = "users"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    hashed_password: Mapped[str]
    is_active: Mapped[bool] = mapped_column(default=True)
    is_superuser: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    last_login: Mapped[datetime | None]
```

### conversations

```python
class ConversationORM(Base):
    __tablename__ = "conversations"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    last_message_at: Mapped[datetime | None]
```

### messages

```python
class MessageORM(Base):
    __tablename__ = "messages"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    conversation_id: Mapped[UUID] = mapped_column(ForeignKey("conversations.id"), nullable=False)
    role: Mapped[MessageRole]           # enum: user | assistant
    content: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    guardrails_score: Mapped[float | None]
```

### exam_sessions

```python
class ExamSessionORM(Base):
    __tablename__ = "exam_sessions"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    conversation_id: Mapped[UUID] = mapped_column(ForeignKey("conversations.id"), nullable=False)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    session_type: Mapped[SessionType]   # enum: mock_generated | real_past_exam
    exam_content: Mapped[dict] = mapped_column(JSONB)
    answer_key: Mapped[dict] = mapped_column(JSONB)
    status: Mapped[SessionStatus]       # enum: in_progress | submitted | graded
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    expires_at: Mapped[datetime]        # created_at + 3 hours
```

**FR-024 enforcement — one active session per user**:
Enforced at the service layer in `exam_service.get_active_session()`. Before creating a new
session, `exam_repo` queries for any existing row where `user_id = :uid AND status = 'in_progress'
AND expires_at > NOW()`. If one exists, `exam_service` raises `ActiveSessionExists`. This is a
service-layer check, not a database constraint, to allow expired sessions to be ignored without
a partial unique index edge case.

### exam_results

```python
class ExamResultORM(Base):
    __tablename__ = "exam_results"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    session_id: Mapped[UUID] = mapped_column(ForeignKey("exam_sessions.id"), nullable=False)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    student_answers: Mapped[dict] = mapped_column(JSONB)
    evaluator_1: Mapped[dict] = mapped_column(JSONB)
    evaluator_2: Mapped[dict] = mapped_column(JSONB)
    total_score_1: Mapped[float]
    total_score_2: Mapped[float]
    discrepancy_flagged: Mapped[bool]
    image_path: Mapped[str | None]      # reserved for future handwritten upload (B1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    # No expires_at — FR-025: results stored permanently
```

**FR-025**: `exam_results` has no TTL or expiry. Rows are permanent. The history view
(`GET /exams/history`) queries this table by `user_id` ordered by `created_at DESC`.

### chunks (pgvector)

```python
class ChunkORM(Base):
    __tablename__ = "chunks"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    source_type: Mapped[str]            # enum: past_exam | answer_key
    year: Mapped[int]
    session: Mapped[int]
    exercise_id: Mapped[int]            # exercise number within exam; pairs question ↔ answer key
    topic: Mapped[str]
    subtopic: Mapped[str]
    question_type: Mapped[str]          # enum: proof | calculation | mcq | sketch
    marks: Mapped[float]
    content: Mapped[str]                # one complete exercise (question + all parts, or answer key)
    embedding: Mapped[Vector(1536)]     # pgvector type
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
```

HNSW index (in Alembic migration):
```sql
CREATE INDEX chunks_embedding_hnsw_idx
ON chunks USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```

### topic_stats

```python
class TopicStatsORM(Base):
    __tablename__ = "topic_stats"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    topic: Mapped[str] = mapped_column(unique=True)
    subtopic: Mapped[str]
    appearances: Mapped[int] = mapped_column(default=0)
    last_seen_year: Mapped[int]
    last_seen_session: Mapped[int]
```

---

## Domain Models (`domain/models.py` — pure Pydantic, no SQLAlchemy)

Domain models are what cross layer boundaries. Services return domain models; repositories
accept and return domain models only. ORM models never leave `repositories/`.

```python
class ExamSession(BaseModel):
    id: UUID
    user_id: UUID
    session_type: SessionType
    status: SessionStatus
    exam_content: ExamContent
    expires_at: datetime

class ExamContent(BaseModel):
    exercises: list[Exercise]

class Exercise(BaseModel):
    id: int
    topic: str
    total_marks: float
    content: str
    graph: GraphSpec | None
    parts: list[ExercisePart]

class ExercisePart(BaseModel):
    part: str
    marks: float
    content: str

class EvaluatorScore(BaseModel):
    scores: dict[str, float]        # {"Q1a": 2.0, "Q1b": 1.0, ...}
    total: float
    feedback: str
    missing_keywords: list[str]

class EvaluationResult(BaseModel):
    session_id: UUID
    evaluator_1: EvaluatorScore
    evaluator_2: EvaluatorScore
    total_score_1: float
    total_score_2: float
    discrepancy_flagged: bool
    discrepancy_details: str | None

class PastQuestion(BaseModel):
    chunk_id: UUID
    year: int
    session: int
    topic: str
    subtopic: str
    question_type: str
    marks: float
    content: str
    answer: str | None              # populated when source_type = answer_key

class TopicStat(BaseModel):
    topic: str
    appearances: int
    last_seen_year: int
    frequency_tier: str             # "high" | "medium" | "low" — computed, not stored

class ErrorResponse(BaseModel):
    error: str
    request_id: str
```

**FR-026 — structured error shape**: All unhandled exceptions are caught at the API boundary
(`api/exceptions.py`) and returned as `ErrorResponse`. The `request_id` is a UUID injected by
middleware at request start and attached to the response headers as `X-Request-ID`.

---

## Enums (`domain/enums.py`)

```python
class SessionType(str, Enum):
    mock_generated = "mock_generated"
    real_past_exam = "real_past_exam"

class SessionStatus(str, Enum):
    in_progress = "in_progress"
    submitted = "submitted"
    graded = "graded"

class QuestionType(str, Enum):
    proof = "proof"
    calculation = "calculation"
    mcq = "mcq"
    sketch = "sketch"

class MessageRole(str, Enum):
    user = "user"
    assistant = "assistant"
```

---

## Domain Exception Hierarchy (`domain/exceptions.py`)

```python
class LebaneseCoachError(Exception): ...        # base

class ExamNotFound(LebaneseCoachError): ...      # 404
class SessionExpired(LebaneseCoachError): ...    # 410 Gone
class ActiveSessionExists(LebaneseCoachError): ...  # 409 Conflict  ← FR-024
class AnswerKeyNotFound(LebaneseCoachError): ...    # 404
class TopicNotFound(LebaneseCoachError): ...        # 404

class AIServiceUnavailable(LebaneseCoachError): ... # 503  ← FR-026
class VaultUnavailable(LebaneseCoachError): ...     # 503 (boot-time, process exits)
class EmbeddingServiceUnavailable(LebaneseCoachError): ... # 503

class InvalidAnswerSubmission(LebaneseCoachError): ... # 422
class OffTopicBlocked(LebaneseCoachError): ...         # 200 (not an error — handled in chat flow)
```

HTTP mapping in `api/exceptions.py`:
| Exception | HTTP Status |
|---|---|
| ExamNotFound, AnswerKeyNotFound, TopicNotFound | 404 |
| ActiveSessionExists | 409 |
| SessionExpired | 410 |
| InvalidAnswerSubmission | 422 |
| AIServiceUnavailable, EmbeddingServiceUnavailable | 503 |

---

## Session State Machine

```
                  ┌─────────────────┐
  POST /exams/    │                 │
  generate  ────► │   in_progress   │
                  │                 │
                  └────────┬────────┘
                           │ POST /exams/{id}/submit
                           ▼
                  ┌─────────────────┐
                  │                 │
                  │    submitted    │
                  │                 │
                  └────────┬────────┘
                           │ dual evaluator completes
                           ▼
                  ┌─────────────────┐
                  │                 │
                  │     graded      │  ──► results saved to exam_results (permanent)
                  │                 │
                  └─────────────────┘

  expires_at < NOW() at any state → session expired (GET /exams/{id} returns 410)
```

**One active session rule (FR-024)**: Transition from `in_progress` → any new session creation
is blocked by `exam_service` until status changes to `submitted`/`graded` or `expires_at` passes.

---

## jsonb Structures (from DECISIONS.md §4)

### exam_content

```json
{
  "exercises": [
    {
      "id": 1,
      "topic": "Functions",
      "total_marks": 4,
      "content": "Let f(x) = \\frac{2}{1 - xe^{-x}}...",
      "graph": {
        "type": "desmos",
        "expression": "y = 2 / (1 - x * e^{-x})",
        "x_range": [-6, 8],
        "y_range": [-4, 4]
      },
      "parts": [
        { "part": "1", "marks": 1, "content": "Determine \\lim_{x \\to -\\infty} f(x)" }
      ]
    }
  ]
}
```

### student_answers

```json
{
  "answers": [
    {
      "exercise_id": 1,
      "parts": [
        {
          "part": "1",
          "answer": "lim = 0 because e^{-x} approaches infinity",
          "submitted_at": "2024-07-03T10:23:00"
        }
      ]
    }
  ]
}
```

### evaluator output (per evaluator_1 / evaluator_2)

```json
{
  "exercise_1": {
    "parts": {
      "1": {
        "score": 0.75,
        "max_score": 1,
        "feedback": "Correct limit but missing asymptote conclusion",
        "missing_keywords": ["horizontal asymptote"]
      }
    },
    "exercise_total": 0.75,
    "exercise_max": 4
  }
}
```

---

## Redis Key Schema

| Key | Type | Value | TTL | Justification |
|---|---|---|---|---|
| `session:{session_id}` | string (JSON) | exam_content + answer_key | 10800 s | Matches 3-hour exam duration; auto-expires stale sessions |
| `guardrails:{session_id}` | string (int) | consecutive off-topic count | 10800 s | Co-expires with session; counter meaningless after session ends |

Constant definitions live in `infra/redis_client.py` as `SESSION_TTL = 10_800` and
`GUARDRAILS_TTL = 10_800`. Every `redis.set()` call MUST pass `ex=SESSION_TTL` or
`ex=GUARDRAILS_TTL` — never omit the TTL argument.
