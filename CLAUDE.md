# Lebanese Math Coach — CLAUDE.md

## What this is

Lebanese GS Grade 12 Math exam prep platform. Students generate mock exams, submit answers for dual AI grading, retrieve past questions, and chat with a curriculum-scoped tutor. Backend is fully built and integrated; frontend shell exists but most pages are `ComingSoon` stubs.

---

## Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.12, FastAPI 0.115, uv |
| ORM | SQLAlchemy 2.0 async (SQLite unsupported — asyncpg only) |
| DB | PostgreSQL 16 + pgvector extension |
| Vector search | asyncpg raw SQL with `<=>` operator (NOT SQLAlchemy — it cannot express pgvector ops without custom types) |
| Secrets | HashiCorp Vault KV v2 — app refuses to boot if unreachable |
| Cache | Redis 7 |
| Object storage | MinIO wired in compose, not yet used by runtime code |
| Auth | fastapi-users 13 + JWT |
| LLM — generation/grading/chat | `claude-sonnet-4-5` |
| LLM — ingestion tagging only | `claude-haiku-4-5-20251001` |
| Embeddings | `voyage-large-2` (1536d) via voyageai SDK |
| Guardrails | NeMo Guardrails sidecar at `http://guardrails:8100` |
| Frontend | React + Vite + TypeScript, hash routing, no react-router-dom yet |
| Containers | Docker Compose (`docker compose up`) |
| Migrations | Alembic — `migrate` container runs `alembic upgrade head` before API starts |

---

## Directory ownership

```
app/
├── api/            HTTP boundary only — routers, request/response shapes, no business logic
│   ├── dependencies.py   FastAPI Depends factories (db session, redis, secrets, auth)
│   ├── exceptions.py     ALL domain→HTTP mappings live here, nowhere else
│   └── routers/    One file per resource: auth, chat, exams, grading, health, questions, textbook, topics
├── services/       Business logic, transaction owners, streaming generators
├── repositories/   SQL only — no HTTP errors, no cache, no domain exceptions raised here
│   ├── orm.py      Single file for all ORM models — never import ORM models outside repositories/
│   └── chunk_repo.py  asyncpg-only (pgvector cosine search); all other repos use SQLAlchemy AsyncSession
├── domain/
│   ├── models.py   Pydantic models that cross layer boundaries — services return these, not ORM models
│   ├── exceptions.py   Domain exception hierarchy — raised by services, mapped to HTTP in api/exceptions.py
│   └── enums.py    SessionType, SessionStatus, QuestionType, MessageRole
└── infra/
    ├── vault.py         resolve_secrets() → AppSecrets; called once at lifespan startup
    ├── auth.py          fastapi-users setup
    ├── redis_client.py  Redis key helpers (guardrails counter, session TTL)
    ├── minio_client.py  Client wrapper — not yet called by runtime code
    ├── llm/
    │   ├── claude.py    stream_claude() → SSE generator; call_claude() → sync blocking
    │   └── tools.py     Tool schema dicts only — no execution logic; ALL_TOOLS list
    └── embeddings/
        └── voyage.py    embed_text() — sync, must be called via asyncio.to_thread()

ingestion/
└── textbook_pipeline.py  Offline CLI: markdown → parse → chunk → tag → embed → pgvector
                          Run: uv run python -m ingestion.textbook_pipeline --textbook-dir textbook/

alembic/versions/
├── 0001_baseline.py   All tables: users, conversations, messages, exam_sessions, exam_results,
│                      chunks (pgvector), topic_stats
└── 0002_textbook.py   textbook_pages table + page_start/page_end nullable cols on chunks

frontend/src/
├── App.tsx          Shell: sidebar, tabbar, hash routing — only Dashboard renders real content
├── pages/
│   ├── Dashboard.tsx  Only fully-ported page
│   └── ComingSoon.tsx  Placeholder for exam, past, topics, chat, history, results
├── lib/
│   ├── icons.tsx    Icon components
│   ├── math.tsx     KaTeX rendering helpers
│   └── ui.tsx       Shared UI primitives
├── data/mock.ts     Hardcoded student fixture (STUDENT object) — not wired to API yet
└── types.ts         PageId, PageProps

specs/
├── 001-lebanese-math-coach/  Original feature spec + contracts (reference only)
└── 002-textbook-rag/         Textbook RAG spec + plan (reference only)
```

---

## Layer rules — never violate these

1. **ORM models never leave `repositories/`**. Services and API receive domain models (`domain/models.py`) or plain dicts. `orm.py` is the single source of truth for ORM definitions.
2. **HTTP errors never appear in services or repositories**. All `HTTPException` or status-code logic lives exclusively in `api/exceptions.py`. Services raise domain exceptions (`LebaneseCoachError` subclasses).
3. **Vault is the only secrets source at runtime**. `AppSecrets` is resolved once in `main.py` lifespan and stored on `app.state.secrets`. Never read `os.environ` for secrets in services.
4. **`embed_text()` is sync**. Always call it with `await asyncio.to_thread(embed_text, ...)`.
5. **`call_claude()` is sync**. Always call it with `await asyncio.to_thread(_call_evaluator, ...)`.
6. **Streaming responses must raise domain exceptions BEFORE the StreamingResponse is constructed**. Once SSE starts (200 + headers sent), exceptions inside the generator cannot map to 4xx. See `grading_service.validate_submission()` + `grading.py` router pattern.
7. **Router registration order in `main.py` is load-bearing**: grading before exams, or `GET /exams/history` is shadowed by `GET /exams/{session_id}`.
8. **`cosine_similarity_search` uses asyncpg directly** (not SQLAlchemy) because pgvector `<=>` requires raw SQL. Always register the vector type with `pgvector.asyncpg.register_vector(conn)` before queries.

---

## Models — locked

| Task | Model ID |
|---|---|
| Exam generation | `claude-sonnet-4-5` |
| Dual evaluator (both) | `claude-sonnet-4-5` |
| Chat | `claude-sonnet-4-5` |
| Textbook tagging (ingestion only) | `claude-haiku-4-5-20251001` |
| Embeddings | `voyage-large-2` (1536d) |

These are hardcoded in `infra/llm/claude.py` and `ingestion/textbook_pipeline.py`. Do not change without checking embedding dimension compatibility.

---

## Database tables

| Table | Key columns | Notes |
|---|---|---|
| `users` | fastapi-users base + created_at, last_login | |
| `conversations` | user_id FK | |
| `messages` | conversation_id FK, role enum, guardrails_score nullable | |
| `exam_sessions` | user_id, session_type, exam_content JSONB, answer_key JSONB, status, expires_at | TTL = 3 hours from creation |
| `exam_results` | session_id, evaluator_1/2 JSONB, total_score_1/2, discrepancy_flagged | Permanent — no expires_at |
| `chunks` | source_type, embedding vector(1536), year/session/exercise_id nullable (NULL for textbook), page_start/page_end nullable (NULL for past exams) | Shared table for past_exam + answer_key + textbook_* source types |
| `textbook_pages` | page_number (unique), chapter, section, page_type, content | Raw page store; chunks join on page_start = page_number |
| `topic_stats` | topic (unique), appearances, last_seen_year | Zero-LLM analytics |

### Redis keys (TTL: 3 hours)
- `guardrails:{conversation_id}` → off-topic message counter (int)
- `session:{session_id}` → `{"answer_key": {...}}` — mirrors DB answer_key for fast grading lookup

---

## Chat SSE event types

Emitted by `POST /chat`:
- `conversation_id` — first turn only
- `token` — streaming text chunk
- `tool_use` — internal only, not forwarded to client
- `textbook_page` — LLM retrieved a specific page
- `textbook_sections` — LLM retrieved textbook sections
- `guardrail_warning` — counter == 2
- `guardrail_block` — counter >= 3 (message blocked, stream ends)
- `done` / `[DONE]`

Guardrail tiers: 0–1 messages = normal, 2 = warning suffix appended, 3+ = block. Messages < 10 words skip the NeMo classification call.

---

## Chat tools (active in `_CHAT_TOOLS`)

Only two tools are active in chat: `retrieve_textbook_page` and `retrieve_textbook_sections`.  
The other three tools (`retrieve_past_questions`, `retrieve_answer_key`, `get_topic_stats`) are defined in `tools.py` but NOT included in `_CHAT_TOOLS`. They are available for future activation.

---

## Ingestion pipeline

Textbook input: markdown files in `textbook/` with YAML frontmatter per page, pages separated by `===PAGE_BREAK===`.

Required frontmatter fields: `page` (int), `chapter`, `section`, `type` (theory | exercise | self_evaluation | mixed | blank | preface | just_for_fun).

Chunk UUID is deterministic: `uuid5(NAMESPACE_OID, f"{source_type}:{page_start}:{page_end}")` — idempotent on re-run.

Past exam ingestion pipeline (`ingestion/pipeline.py` in spec 001) is not yet written — only the textbook pipeline exists.

---

## Frontend state

- **Dashboard** — only fully-ported page with real UI
- **All other pages** (exam, past, topics, chat, history, results) — `ComingSoon` stubs
- Auth not wired to frontend yet — `data/mock.ts` hardcodes a student fixture
- No API calls from frontend yet

---

## Hard rules

- Never append `Co-Authored-By` to git commit messages.
- Do not add try/except around internal calls that cannot fail (SQLAlchemy session ops, dict access on validated Pydantic models).
- Do not create new top-level directories — all backend code lives under `app/` or `ingestion/`.
- New exceptions go in `domain/exceptions.py` and must be mapped in `api/exceptions.py` before the router is added.
- New LLM tools go in `infra/llm/tools.py` as plain dicts. Tool dispatch goes in the service layer.
- `docker compose up` starts all services. `docker compose run --rm migrate` runs migrations standalone.
