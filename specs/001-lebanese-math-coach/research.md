# Research: Lebanese Math Coach

**Phase 0 note**: The user supplied the complete stack and all architectural decisions in the
`/speckit-plan` invocation and in `DECISIONS.md`. There are **no NEEDS CLARIFICATION items** in
Technical Context. This document records the decisions already made, the pattern chosen for each,
and why it was preferred over alternatives — so implementers have the rationale at hand.

---

## Decision 1 — SSE Streaming for Claude Responses

**Decision**: All Claude API calls use `stream=True`. FastAPI routes that trigger LLM responses
return `StreamingResponse` with `media_type="text/event-stream"`.

**Pattern**:
```python
# infra/llm/claude.py
async def stream_claude(messages, system, tools=None):
    with anthropic_client.messages.stream(
        model="claude-sonnet-4-5",
        system=system,
        messages=messages,
        tools=tools or [],
    ) as stream:
        for text in stream.text_stream:
            yield f"data: {json.dumps({'text': text})}\n\n"
    yield "data: [DONE]\n\n"

# api/routers/chat.py
return StreamingResponse(stream_claude(...), media_type="text/event-stream")
```

**Rationale**: Exam generation takes 5–15 s. Without streaming, students see a blank screen for
the full duration. SSE delivers tokens as they arrive, making the experience feel responsive.

**Alternative rejected**: WebSocket — adds bidirectional complexity not needed for unidirectional
LLM output.

---

## Decision 2 — pgvector Cosine Similarity Query

**Decision**: Use pgvector's `<=>` cosine distance operator with an HNSW index on `chunks.embedding`.

**Pattern**:
```sql
-- chunk_repo.py
SELECT id, content, topic, subtopic, year, session, marks
FROM chunks
WHERE source_type = :source_type
  AND year BETWEEN :year_from AND :year_to
ORDER BY embedding <=> :query_vector
LIMIT :k;
```

**Index**:
```sql
CREATE INDEX ON chunks USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```

**Rationale**: HNSW gives sub-linear approximate nearest-neighbour search. `<=>` is cosine
distance (1 - cosine_similarity), so ascending ORDER BY returns most similar first.

**Alternative rejected**: Exact scan (`<->` L2) — slower at scale; IVFFlat — requires knowing
`nlist` in advance; not appropriate for 20-exam archive size.

---

## Decision 3 — Vault Fail-Fast at Startup

**Decision**: `infra/vault.py` is called in FastAPI's `lifespan` startup event. If Vault is
unreachable, the function raises `VaultUnavailable` and the process exits before serving any
request.

**Pattern**:
```python
# infra/vault.py
def resolve_secrets() -> AppSecrets:
    client = hvac.Client(url=VAULT_ADDR, token=VAULT_TOKEN)
    if not client.is_authenticated():
        raise VaultUnavailable("Vault unreachable or token invalid")
    data = client.secrets.kv.read_secret_version(path="lebanese-math-coach")
    return AppSecrets(**data["data"]["data"])

# main.py
@asynccontextmanager
async def lifespan(app: FastAPI):
    secrets = resolve_secrets()   # raises on failure → process dies
    app.state.secrets = secrets
    yield
```

**Rationale**: Constitution Principle II — app must refuse to boot if Vault unreachable. A
running app with missing credentials would silently fail at first LLM call. Fail-fast surfaces
the problem immediately.

**Alternative rejected**: Lazy resolution per-request — violates constitution; masks boot errors.

---

## Decision 4 — Dual Evaluator with asyncio.gather

**Decision**: The two claude-sonnet-4-5 evaluation calls are dispatched concurrently with
`asyncio.gather`, not sequentially. Both receive the same student answers and answer key.

**Pattern**:
```python
# services/grading_service.py
async def run_dual_evaluator(answers, answer_key, exam_content):
    evaluator_1, evaluator_2 = await asyncio.gather(
        call_evaluator(answers, answer_key, exam_content, persona="strict"),
        call_evaluator(answers, answer_key, exam_content, persona="lenient"),
    )
    discrepancy = detect_discrepancy(evaluator_1, evaluator_2)
    return EvaluationResult(
        evaluator_1=evaluator_1,
        evaluator_2=evaluator_2,
        discrepancy_flagged=discrepancy.flagged,
        discrepancy_details=discrepancy.details,
    )
```

**Rationale**: Running both evaluators in parallel halves latency (two ~30 s calls → ~30 s total
instead of ~60 s). The evaluators are fully independent — no shared state.

**Alternative rejected**: Sequential calls — doubles latency for no benefit; multi-agent
orchestration framework — unnecessary overhead for exactly two fixed parallel calls.

---

## Decision 5 — Guardrails: Cosine Similarity on First Message Only

**Decision**: Only the first student message in a session that exceeds 10 words is checked via
cosine similarity against math-education anchor embeddings. Subsequent messages use system-prompt
guardrails only. The off-topic counter (consecutive count) is stored in Redis with a 3-hour TTL.

**Three-tier response logic** (evaluated per turn in `guardrails_service.py`):
- Counter = 0 or 1: normal response
- Counter = 2: append gentle redirect reminder to system prompt
- Counter ≥ 3: return soft-block message, skip LLM call

**Anchor embeddings** (pre-computed at startup, stored in memory):
```python
ANCHOR_TEXTS = [
    "Lebanese baccalaureate math exam question",
    "GS Grade 12 mathematics problem solving",
    "Lebanese official exam past paper solution",
]
```

**Rationale**: Full cosine check on every message is expensive and unnecessary — the system prompt
handles most off-topic cases. The first-message check catches students who start entirely off-topic
before any context is established.

**Alternative rejected**: Dedicated claude-haiku classification call per message — 3× more
expensive; adds latency; system prompt is sufficient for subsequent turns.

---

## Decision 6 — Redis Session Management

**Decision**: Active exam sessions are stored as JSON strings in Redis with explicit TTL constants
defined once in `infra/redis_client.py`. Two key prefixes:

| Key | Value | TTL |
|---|---|---|
| `session:{session_id}` | JSON: exam_content + answer_key | 10800 s (3 h) |
| `guardrails:{session_id}` | int: consecutive off-topic count | 10800 s (3 h) |

**Pattern**:
```python
# infra/redis_client.py
SESSION_TTL = 10_800   # 3 hours — matches real exam duration; justified: active exam data
GUARDRAILS_TTL = 10_800  # 3 hours — co-expires with session; no stale counters

async def set_session(redis, session_id: str, data: dict) -> None:
    await redis.set(f"session:{session_id}", json.dumps(data), ex=SESSION_TTL)
```

**Rationale**: Exam content + generated answer key must be fast-access (sub-millisecond) during
an active 3-hour session. PostgreSQL `exam_sessions` stores durable metadata; Redis holds
hot session data. TTL matches exam duration so keys self-clean without a background job.

**Alternative rejected**: PostgreSQL only — too slow for per-request session reads during active
exam; no TTL mechanism without cron jobs.

---

## Decision 7 — PDF Chunking Strategy

**Decision**: Exercise-level chunking — one chunk per complete exercise (question + all its
parts). One chunk per complete answer key exercise. Chunk boundaries always align with exercise
boundaries; a single exercise is never split across two chunks. Diagram images are skipped
(text-only). Each chunk is tagged by `claude-haiku` with: topic, subtopic, question_type.

**Pairing**: Answer key chunks are paired with their corresponding question chunk via
`exercise_id` (same `year` + `session` + `exercise_id`). The `retrieve_answer_key` agent tool
fetches answer key chunks using an exact metadata filter, not cosine similarity.

**Chunk metadata stored per chunk in pgvector `chunks` table**:
`source_type`, `year`, `session`, `exercise_id`, `topic`, `subtopic`, `question_type`, `marks`,
`content`, `embedding` (vector 1536).

**Rationale**: Lebanese GS Math exam exercises are self-contained units. A question and its
parts form one logical retrieval unit — splitting mid-exercise would degrade both embedding
quality and retrieval coherence. Exercise-level chunks also make answer key pairing trivial:
match on `(year, session, exercise_id, source_type='answer_key')` without any similarity search.

**Alternative rejected**: Fixed-size 500–800 token window with overlap — splits exercises at
arbitrary token boundaries, breaking the semantic unit. Sentence-level — far too granular for
multi-part exam questions.

---

## Decision 8 — fastapi-users JWT Configuration

**Decision**: `fastapi-users` 13.x with `JWTStrategy`. Bearer token auth. `UserManager` subclass
handles registration and login. `SECRET` for JWT signing comes from Vault (via `app.state.secrets`
at startup).

**Rationale**: `fastapi-users` provides a complete, tested auth solution (register, login,
forgot-password, current-user dependency) without requiring custom user management code.
JWT is stateless — fits Docker Compose deployment without a shared session store.

**Alternative rejected**: Custom JWT implementation — not justified; fastapi-users handles edge
cases (inactive users, superuser checks) already. Session cookies — stateful, adds Redis
dependency for auth (Redis is already used for exam sessions but mixing concerns would be messy).

---

## Decision 9 — Curriculum JSON Injection

**Decision**: The curriculum JSON (defining in-scope/out-of-scope topics) is read from disk at
startup and injected directly into every system prompt. It is never stored in pgvector or
retrieved via RAG.

**Rationale**: The curriculum JSON is small (< 2000 tokens), fully deterministic, and must
apply to every interaction. RAG retrieval would add latency and risk partial retrieval. Direct
injection guarantees the model always sees the full curriculum scope.

**File location**: `app/data/curriculum.json` (mounted into Docker container).

---

## Decision 10 — Few-Shot Examples in Generation Prompt

**Decision**: The 2–3 most recent English-track past exams are included as few-shot examples
directly in the system prompt for exam generation. These are loaded from disk at startup (not
retrieved via RAG).

**Rationale**: Exam structure is highly consistent year-to-year. Static few-shot examples
are more reliable than dynamic RAG retrieval for structural grounding. 2–3 full exams fit
comfortably within Claude's context window alongside the curriculum JSON.

**File location**: `app/data/few_shot_exams/` — 2–3 manually selected exam JSON files.
