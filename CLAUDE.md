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
| Observability | Langfuse v2 self-hosted at `http://localhost:3001` (pinned `langfuse/langfuse:2`) |
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
├── utils.py        Shared utility functions (parse_json_response — strips fences, parses JSON)
└── infra/
    ├── vault.py              resolve_secrets() → AppSecrets; called once at lifespan startup
    ├── auth.py               fastapi-users setup
    ├── redis_client.py       Redis key helpers (guardrails counter, session TTL)
    ├── minio_client.py       Client wrapper — not yet called by runtime code
    ├── langfuse_client.py    Lazy singleton; get_prompt() with fallback; trace() context manager
    ├── llm/
    │   ├── claude.py    stream_claude() → SSE generator; call_claude() → sync blocking
    │   └── tools.py     Tool schema dicts only — no execution logic; ALL_TOOLS list
    └── embeddings/
        └── voyage.py    embed_text() — sync, must be called via asyncio.to_thread()

prompts/
├── shared/          Subject-agnostic — zero subject references anywhere in these files
│   ├── chat.py          build_retrieve_user_message
│   ├── extraction.py    build_extraction_prompt
│   ├── exam_generation.py  JUDGE_SYSTEM_PROMPT
│   └── grading.py       build_evaluator_prompt, _format_exam/_answer_key/_answers helpers
└── math/            Lebanese GS Grade 12 Math specific
    ├── chat.py              build_chat_system_prompt, IMAGE_EXTRACT_PROMPT, RETRIEVE_SYSTEM_PROMPT,
    │                        BLOCK_MESSAGE, WARNING_SUFFIX
    ├── exam_generation.py   build_generation_system_prompt, VALIDATOR_SYSTEM_PROMPT, REGENERATE_SYSTEM_PROMPT
    ├── grading.py           PERSONA_INSTRUCTIONS, build_pdf_evaluator_prompt
    ├── official_exam_parsing.py  SYSTEM_PROMPT, EXTRACTION_SYSTEM_PROMPT, parse_exam_response
    └── tagging_past_exams.py  TAG_PROMPT (ingestion only)

ingestion/
├── textbook_pipeline.py      Offline CLI: markdown → parse → textbook_pages (no chunking/tagging/embedding)
│                             Run: uv run python -m ingestion.textbook_pipeline --textbook-dir textbook/
└── official_exam_pipeline.py  PDF → Claude extraction → PostgreSQL + MinIO

scripts/
└── seed_langfuse_prompts.py  Idempotent — pushes all prompts/ constants to Langfuse as "production" label.
                              Run after adding or editing any prompt constant.
                              STATIC_PROMPT_NAMES maps Python (module, attr) → Langfuse name; must stay
                              in sync with every get_prompt() call site in app/.

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
| Embeddings | `voyage-large-2` (1536d) |

These are hardcoded in `infra/llm/claude.py`. Do not change without checking embedding dimension compatibility.

---

## Database tables

| Table | Key columns | Notes |
|---|---|---|
| `users` | fastapi-users base + created_at, last_login | |
| `conversations` | user_id FK | |
| `messages` | conversation_id FK, role enum | |
| `exam_sessions` | user_id, session_type, exam_content JSONB, answer_key JSONB, status | Permanent — no expires_at |
| `exam_results` | session_id, evaluator_1/2 JSONB, total_score_1/2, discrepancy_flagged | Permanent — no expires_at |
| `chunks` | source_type, embedding vector(1536), year/session/exercise_id nullable | Shared table for past_exam + answer_key source types — textbook content is no longer chunked/embedded, see `textbook_pages` |
| `textbook_pages` | page_number (unique), chapter, section, page_type, content | Raw page store; looked up directly by page_number, not joined from `chunks` |
| `topic_stats` | topic (unique), appearances, last_seen_year | Zero-LLM analytics |
| `guardrail_events` | user_id, conversation_id nullable, source/direction/category/level enums, score, reason, text_hash, text_preview | Audit log for the guardrails system — text_preview is truncated + PII-redacted, never the raw message |

### Redis keys
- `guardrails:{conversation_id}` → off-topic message counter (int), TTL 3 hours
- `session:{session_id}` → `{"answer_key": {...}}` — written on exam creation (TTL 3 hours), mirrors `exam_sessions.answer_key`; not currently read back by any code path (grading reads the answer key from Postgres directly)

---

## Chat SSE event types

Emitted by `POST /chat`:
- `conversation_id` — first turn only
- `token` — streaming text chunk
- `tool_use` — internal only, not forwarded to client
- `textbook_page` — LLM retrieved a specific page
- `guardrail_warning` — counter == 2
- `guardrail_block` — counter >= 3 (message blocked, stream ends)
- `done` / `[DONE]`

Guardrail tiers: 0–1 messages = normal, 2 = warning suffix appended, 3+ = block. Messages < 10 words skip the NeMo classification call.

---

## Chat tools (active in `_CHAT_TOOLS`)

Only one tool is active in chat: `retrieve_textbook_page` (direct page-number lookup against `textbook_pages` — no embeddings involved).
The other three tools (`retrieve_past_questions`, `retrieve_answer_key`, `get_topic_stats`) are defined in `tools.py` but NOT included in `_CHAT_TOOLS`. They are available for future activation.

---

## Guardrails

Two-tier severity model, both driven by one classifier call per message
(`guardrails_service.classify_input`, calling the NeMo sidecar's `POST /check`):

- **`off_topic`** — lenient. Redis counter (`guardrails:{conversation_id}`,
  TTL 3 hours): 0–1 consecutive off-topic messages = normal, 2 = warning
  suffix appended, 3+ = block.
- **`prompt_injection` / `harmful_content`** — zero-tolerance. Blocks that
  single message immediately, no counter, no grace period.

Every block path (zero-tolerance or 3-strike) persists a paired assistant
message before returning — required for Anthropic's API, which rejects
consecutive same-role messages on the next turn.

Generated content (chat replies, exam exercises) is also screened via a
separate, simpler action (`classify_output`, `POST /check-output` on the
sidecar) that only asks "is this safe to show a student" — no
adversarial-intent categories, since those don't apply to the model's own
output. Exam generation blocks on a flagged result (not streamed, so
blocking is feasible before anything is shown). Chat output is audited in
a non-blocking background task (`audit_output_async`) — log-only, since
the reply is already streamed by the time the full text exists.

Every blocked/warned event is persisted to `guardrail_events` (`source`:
chat | exam_generation; `direction`: input | output) — this is what
backs the admin Guardrails page. `text_preview` is PII-redacted
(Presidio, scoped to this audit-log field only — never applied to live
chat content, since Presidio's NER false-positives on math notation).

---

## Langfuse observability

Langfuse v2 runs as a Docker Compose service (`langfuse` + `langfuse-db`), available at `http://localhost:3001`. Dev credentials are pre-provisioned via `LANGFUSE_INIT_*` env vars — no manual UI setup needed.

**Keys:** `langfuse_public_key` / `langfuse_secret_key` live in Vault (via `seed_vault.sh`) and are loaded into `AppSecrets`. `LANGFUSE_HOST` is a non-secret env var on the api service (same pattern as `GUARDRAILS_URL`).

**Client:** `app/infra/langfuse_client.py` — lazy singleton. Never raises. Langfuse being down must never break the app.
- `get_prompt(secrets, name, fallback=...)` — fetches from Langfuse with `max_retries=1, fetch_timeout_seconds=3`; returns fallback string if unreachable
- `trace(secrets, name, ...)` — context manager; `handle.input/output/model/usage` fields captured on exit

**Every Claude call is traced.** `stream_claude`, `call_claude`, `call_claude_vision` all accept `secrets`, `trace_name`, `user_id`, `session_id` kwargs and wrap their call in `langfuse_client.trace()`.

**Prompt management:**
- *Static prompts* (plain string constants) — fetched live from Langfuse at runtime via `get_prompt()`; Python constant is the fallback only
- *Dynamic builders* (`build_*()` functions) — stay in Python permanently; f-string interpolation and embedded JSON schemas collide with Langfuse `{{mustache}}` syntax. Rendered snapshots are pushed to Langfuse for visibility only (named `*_snapshot`, never fetched)
- Run `scripts/seed_langfuse_prompts.py` after adding or editing any prompt constant

---

## Prompts architecture

`prompts/` is split into two tiers enforced by a strict rule: **`shared/` files must contain zero subject-specific references**.

- `shared/` — structural code reusable for any exam subject (generic builders, format helpers, subject-agnostic prompt constants)
- `math/` — Lebanese GS Grade 12 Math specific (curriculum references, LaTeX rules, Lebanese baccalaureate context)
- To add a new subject: create `prompts/{subject}/` following the same split

Dynamic builders stay in Python even when they look like templates — see Langfuse section above for why.

`parse_json_response()` in `app/utils.py` is the shared Claude-response JSON parser. Do not add response-parsing logic to `prompts/`.

---

## Ingestion pipeline

Textbook input: markdown files in `textbook/` with YAML frontmatter per page, pages separated by `===PAGE_BREAK===`.

Required frontmatter fields: `page` (int), `chapter`, `section`, `type` (theory | exercise | self_evaluation | mixed | blank | preface | just_for_fun).

Textbook ingestion only parses pages into `textbook_pages` (upsert on `page_number`, idempotent on re-run) — it does not chunk, tag, or embed. Retrieval over textbook content is page-number lookup only (`retrieve_textbook_page`), not semantic search.

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
- New prompt constants go in `prompts/shared/` (if zero subject refs) or `prompts/math/` (if any Lebanese GS / math reference). After adding, run `seed_langfuse_prompts.py` and add the name to `STATIC_PROMPT_NAMES` if it will be fetched at runtime via `get_prompt()`.
- `docker compose up` starts all services. `docker compose run --rm migrate` runs migrations standalone.
