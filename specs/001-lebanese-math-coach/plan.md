# Implementation Plan: Lebanese Math Coach

**Branch**: `001-lebanese-math-coach` | **Date**: 2026-06-03 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-lebanese-math-coach/spec.md`

## Summary

Lebanese Math Coach is a full-stack web application for Lebanese GS Grade 12 students preparing
for the official baccalaureate math exam. Students can generate curriculum-scoped mock exams,
submit typed answers, receive grading from two independent AI evaluators (strict vs. lenient),
retrieve past official exam questions by topic and year, study topic frequency analytics, and ask
the AI coach for Lebanon-grounded topic explanations — all within a guardrailed, streaming chat
interface.

The backend is a FastAPI service following the constitution's five-layer architecture
(api/services/repositories/domain/infra), backed by PostgreSQL 16 + pgvector for embeddings and
structured data, Redis 7 for session state, MinIO for PDF storage, and HashiCorp Vault for all
secrets. The frontend is a React 18 + Vite + TypeScript SPA with KaTeX math rendering and SSE
streaming for all AI responses. An offline ingestion pipeline (not a runtime feature) processes 20
past official English-track GS Math exams from Apelr into pgvector chunks tagged by claude-haiku.

## Technical Context

**Language/Version**: Python 3.12 (backend), TypeScript 5.x (frontend)

**Package Manager**: uv (Python), npm (frontend)

**Primary Dependencies**:
- Backend: FastAPI 0.115, SQLAlchemy 2.0 async, fastapi-users 13.x, anthropic SDK,
  voyageai, redis-py 5.x, minio, hvac (Vault), pdfplumber, pgvector, alembic
- Frontend: React 18, Vite 5, TypeScript, KaTeX, Tailwind CSS 3.x

**Storage**: PostgreSQL 16 + pgvector (primary data + 1536d embeddings), Redis 7 (sessions TTL 3h,
guardrails counter TTL 3h), MinIO (raw PDFs)

**Testing**: pytest + pytest-asyncio (backend), Vitest (frontend)

**Target Platform**: Docker Compose on Linux containers; desktop browser (Chrome/Firefox/Safari)

**Project Type**: Full-stack web service (FastAPI backend + React SPA frontend)

**Performance Goals**:
- Mock exam generation: first streamed token < 5 s, complete < 30 s
- Dual evaluation (parallel): both results displayed < 60 s
- Topic analytics dashboard: < 3 s (pure SQL, zero LLM)
- Past question retrieval: < 5 s (pgvector similarity search)

**Constraints**:
- App MUST refuse to boot if Vault unreachable (hvac check at startup)
- Alembic migrate container MUST exit 0 before API container starts
- All Claude responses MUST stream via SSE — never buffered JSON
- All Redis keys MUST carry explicit TTL set at write time
- No ORM model MUST cross layer boundary into services/ or api/

**Scale/Scope**: Demo-scale — 1–5 concurrent users for MVP

## Constitution Check — Phase 0 Gate

*GATE: Must pass before Phase 0 research.*

| Principle | Status | Verification |
|---|---|---|
| I. Layered Architecture | PASS | api/services/repositories/domain/infra defined; routers depend only on domain models and Depends() |
| II. Infrastructure Contracts | PASS | hvac.Client health check at app startup in infra/vault.py; docker-compose depends_on migrate with service_completed_successfully |
| III. Streaming Runtime | PASS | All Claude calls use stream=True + SSE response; Redis TTLs documented per key in infra/redis_client.py |
| IV. Error Boundaries | PASS | domain/exceptions.py defines hierarchy; api/exceptions.py maps each to HTTP; services raise domain exceptions only |
| V. Security | PASS | All secrets from Vault; Pydantic models validate every API request body and path/query params |

*No violations. Complexity Tracking section not required.*

## Project Structure

### Documentation (this feature)

```text
specs/001-lebanese-math-coach/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   ├── auth.md
│   ├── exams.md
│   ├── grading.md
│   ├── questions.md
│   ├── topics.md
│   └── chat.md
└── tasks.md             # Phase 2 output (/speckit-tasks — NOT created here)
```

### Source Code (repository root)

```text
app/
├── api/
│   ├── routers/
│   │   ├── auth.py          # /auth — fastapi-users router
│   │   ├── exams.py         # /exams — generate, get active, get by id
│   │   ├── grading.py       # /exams/{id}/submit, /exams/{id}/results, /exams/history
│   │   ├── questions.py     # /questions/retrieve — semantic RAG search
│   │   ├── topics.py        # /topics/stats, /topics/{topic}/questions
│   │   └── chat.py          # /chat — SSE streaming endpoint
│   ├── dependencies.py      # Depends: current_user, db_session, redis, vault secrets
│   └── exceptions.py        # @app.exception_handler mapping domain → HTTP + request_id
│
├── services/
│   ├── exam_service.py      # generate_exam(), start_session(), get_active_session()
│   ├── grading_service.py   # submit_answers(), run_dual_evaluator(), get_results()
│   ├── retrieval_service.py # retrieve_past_questions(), retrieve_answer_key()
│   ├── topic_service.py     # get_all_topic_stats(), get_questions_by_topic()
│   ├── chat_service.py      # handle_turn(), build_system_prompt()
│   └── guardrails_service.py# classify_message(), get_counter(), increment_counter()
│
├── repositories/
│   ├── exam_repo.py         # exam_sessions + exam_results CRUD
│   ├── chunk_repo.py        # cosine similarity search on chunks table
│   ├── topic_stats_repo.py  # topic_stats COUNT and ranking queries
│   ├── user_repo.py         # users CRUD (thin wrapper over fastapi-users)
│   └── message_repo.py      # conversations + messages CRUD
│
├── domain/
│   ├── models.py            # Pydantic domain models (never ORM models)
│   ├── exceptions.py        # ExamNotFound, SessionExpired, ActiveSessionExists,
│   │                        # VaultUnavailable, AIServiceUnavailable, etc.
│   └── enums.py             # SessionType, SessionStatus, QuestionType, MessageRole
│
└── infra/
    ├── vault.py             # resolve_secrets() — blocks startup if unreachable
    ├── redis_client.py      # get_redis(); SESSION_TTL=10800, GUARDRAILS_TTL=10800 constants
    ├── minio_client.py      # get_minio_client(), upload_pdf(), get_pdf_bytes()
    └── llm/
        ├── claude.py        # stream_claude(), call_claude(); wraps anthropic SDK
        └── tools.py         # Tool schema definitions for all 3 agent tools
    └── embeddings/
        └── voyage.py        # embed_text(), embed_batch() via voyageai
                             # (NOTE: the original cosine-anchor guardrails.py was removed —
                             #  off-topic checks now live in the guardrails-service, see below)

alembic/
├── env.py
└── versions/
    └── 0001_baseline.py     # initial schema from DECISIONS.md §4

ingestion/                   # offline pipeline — no runtime coupling to app/
├── pipeline.py              # orchestrate: MinIO → extract → chunk → tag → embed → store
├── pdf_extractor.py         # pdfplumber text-only extraction (images skipped)
├── chunker.py               # exercise-level chunking; one chunk per complete exercise, never split across exercise boundaries
├── tagger.py                # claude-haiku: topic + subtopic + question_type per chunk
└── embedder.py              # voyageai voyage-large-2 batch embed → pgvector INSERT

guardrails-service/          # standalone off-topic classifier microservice (own container)
├── main.py                  # FastAPI: POST /check → {"off_topic": bool}; NeMo LLMRails
├── Dockerfile
├── requirements.txt         # nemoguardrails, langchain, langchain-anthropic, fastapi
└── config/
    ├── config.yml           # NeMo: main engine = anthropic claude-haiku-4-5
    └── rails.co             # input flow: check_math_topic action → "OFF_TOPIC" sentinel

frontend/
├── src/
│   ├── components/
│   │   ├── exam/            # ExamRenderer (KaTeX), QuestionCard, AnswerInput, SessionTimer
│   │   ├── results/         # DualScoreCard, DiscrepancyBadge, FeedbackPanel, HistoryList
│   │   ├── topics/          # TopicTable, FrequencyBadge, TopicQuestionList
│   │   └── chat/            # ChatThread, StreamingMessage, GuardrailBanner
│   ├── pages/
│   │   ├── ExamPage.tsx
│   │   ├── ResultsPage.tsx
│   │   ├── QuestionsPage.tsx
│   │   ├── TopicsPage.tsx
│   │   ├── ChatPage.tsx
│   │   └── HistoryPage.tsx
│   ├── services/
│   │   ├── api.ts           # typed fetch wrappers for all REST endpoints
│   │   └── sse.ts           # SSE client: EventSource wrapper + token accumulator
│   └── hooks/
│       ├── useExamSession.ts
│       ├── useSSEStream.ts
│       └── useTopicStats.ts
└── vite.config.ts

docker-compose.yml           # services: db, redis, minio, vault, vault-seed, migrate,
                             # guardrails, api, pgadmin
.env.example                 # VAULT_TOKEN only — all other secrets live in Vault
```

**Structure Decision**: Full-stack web application. Backend under `app/` strictly following the
constitution's five-layer structure. Frontend under `frontend/` as a standalone Vite SPA.
Ingestion under `ingestion/` as an isolated offline pipeline with no import-time coupling to
`app/`. Alembic under `alembic/` at repo root. Off-topic guardrail classification runs as a
standalone `guardrails-service/` container (NeMo Guardrails + Claude Haiku); the main API calls
it over HTTP via `GUARDRAILS_URL` and keeps all counter/tier/blocking logic in
`services/guardrails_service.py`. All services orchestrated via `docker-compose.yml`.

**Guardrails design note (deviation from original plan)**: The plan originally specified an
in-process cosine-anchor embedding check (`infra/embeddings/guardrails.py`). During Phase 4 this
was replaced by a dedicated NeMo Guardrails microservice that makes a single Claude Haiku
classification call per message. The old embedding module was removed. The microservice receives
`ANTHROPIC_API_KEY` via Compose env rather than Vault — a
deliberate, documented exception to the Vault-first principle (the service has no runtime Vault
dependency).

## Implementation Phases

2-week build order. Each phase produces a shippable increment that can be demoed independently.
Fallback order (if time runs short): Vault → `.env`, MinIO → local storage, topic analytics UI,
dynamic guardrails, auth — drop in that order and document in this section.

### Phase 1 — Infrastructure Foundation (Days 1–2)

**Goal**: Every service running, secrets wired, database migrated, API boots.
**User stories unblocked**: none yet — this is the prerequisite for everything.

| Task | Deliverable |
|---|---|
| Docker Compose: api, db, redis, minio, vault, migrate | All 6 services healthy |
| `infra/vault.py` — resolve_secrets(), fail-fast at startup | App refuses to boot if Vault down |
| Alembic baseline migration — all tables + pgvector extension + HNSW index | `alembic upgrade head` exits 0 |
| `infra/redis_client.py` — SESSION_TTL + GUARDRAILS_TTL constants | Redis CRUD helpers with TTL |
| fastapi-users JWT auth wired | `POST /auth/register` + `POST /auth/jwt/login` working |
| `GET /health` endpoint | Returns vault/db/redis status |

**Checkpoint**: `docker-compose up` → all services healthy → `curl /health` returns ok.

---

### Phase 2 — Ingestion Pipeline (Day 3)

**Goal**: Past exam PDFs ingested into pgvector; topic_stats populated.
**Note**: Offline pipeline — not a runtime API feature. Prerequisite for all RAG features.

| Task | Deliverable |
|---|---|
| `ingestion/pdf_extractor.py` — pdfplumber text-only extraction | Text extracted from all 20 PDFs |
| `ingestion/chunker.py` — exercise-level chunking | One chunk per complete exercise |
| `ingestion/tagger.py` — claude-haiku topic/subtopic/question_type tagging | All chunks tagged |
| `ingestion/embedder.py` — voyage-large-2 batch embed + pgvector INSERT | Chunks stored with exercise_id |
| topic_stats populated | `SELECT COUNT(*) FROM topic_stats` returns ~12 rows |

**Checkpoint**: `python -m ingestion.pipeline` completes → `SELECT COUNT(*) FROM chunks` ~115 rows (19 exams × ~6 exercises each).

---

### Phase 3 — RAG Retrieval + Topic Analytics (Day 4)

**Goal**: Past questions retrievable by topic/year; topic frequency dashboard working.
**User stories**: US3 (past question retrieval), US4 (topic analytics).

| Task | Deliverable |
|---|---|
| `repositories/chunk_repo.py` — cosine similarity search | `POST /questions/retrieve` returns ranked results |
| `repositories/topic_stats_repo.py` — ranking query | `GET /topics/stats` returns frequency-tiered topics |
| `services/retrieval_service.py` — retrieve_past_questions tool | Agent tool wired |
| `services/topic_service.py` — get_all_topic_stats, get_questions_by_topic | `GET /topics/{topic}/questions` working |

**Checkpoint**: Query returns relevant past questions for "integration 2015–2024"; topic stats load in < 3 s.

---

### Phase 4 — Exam Generation + Chat (Day 5)

**Goal**: Mock exam generated via streaming SSE; topic explanation chat working.
**User stories**: US1 (mock exam generation), US5 (topic explanation), US6 (curriculum scope), US7 (guardrails).

| Task | Deliverable |
|---|---|
| `app/data/curriculum.json` — current year scope | Loaded at startup, injected into every system prompt |
| `app/data/few_shot_exams/` — 2–3 recent exams | Few-shot examples baked into generation prompt |
| `infra/llm/claude.py` — stream_claude() + SSE response | First token < 5 s |
| `infra/llm/tools.py` — 3 agent tool definitions | retrieve_past_questions, retrieve_answer_key, get_topic_stats |
| `services/exam_service.py` — generate_exam(), FR-024 active session check | `POST /exams/generate` streams exam |
| `guardrails-service/` (NeMo + Claude Haiku) + `services/guardrails_service.py` HTTP client + Redis counter | Three-tier response logic |
| `services/chat_service.py` — handle_turn(), curriculum scope check | `POST /chat` streams response |

**Checkpoint**: Mock exam generates and streams; asking about out-of-scope topic returns correct notice; 3 off-topic messages triggers soft block.

---

### Phase 5 — Dual Evaluator + Results (Days 6–7)

**Goal**: Answer submission triggers parallel grading; results stored permanently.
**User stories**: US2 (dual evaluation + discrepancy visibility).

| Task | Deliverable |
|---|---|
| `services/grading_service.py` — asyncio.gather dual evaluator | Two parallel claude-sonnet-4-5 calls |
| Strict evaluator system prompt | Deducts on doubt |
| Lenient evaluator system prompt | Awards on doubt |
| Discrepancy detection | `discrepancy_flagged` = true when per-question scores differ |
| `repositories/exam_repo.py` — save exam_results (permanent, no TTL) | FR-025: results stored forever |
| `GET /exams/{id}/results` + `GET /exams/history` | Results and history endpoints working |

**Checkpoint**: Submit exam → both evaluators return within 60 s → discrepancies flagged → history endpoint returns all past results.

---

### Phase 6 — React Frontend (Day 8)

**Goal**: Students can use the full platform in a browser.
**User stories**: All (UI for every backend feature).

| Task | Deliverable |
|---|---|
| Vite + React 18 + TypeScript + Tailwind + KaTeX scaffold | `npm run dev` starts |
| `services/sse.ts` — SSE client with token accumulator | Streaming text renders incrementally |
| ExamPage — generate + render exam with KaTeX | Exam displays with math notation |
| ResultsPage — dual score cards + DiscrepancyBadge | Side-by-side evaluator comparison |
| TopicsPage — TopicTable with FrequencyBadge | Color-coded frequency table |
| ChatPage — ChatThread + StreamingMessage + GuardrailBanner | Streaming chat with guardrail states |
| HistoryPage — list of past exam results | Permanent history accessible |

**Checkpoint**: Full end-to-end flow works in browser: register → generate exam → answer → submit → see dual results.

---

### Phase 7 — Polish + Demo Prep (Day 9–10)

**Goal**: Stable, demo-ready platform.

| Task | Deliverable |
|---|---|
| Error states — 503 retry UI, 409 active session warning, 410 expired session | FR-026 UX complete |
| `GET /health` includes all service statuses | Visible in demo |
| Smoke test pass end-to-end | All 9 SC-00x success criteria verified |
| Fallback decisions documented if any phases were deferred | This section updated |

---

## Constitution Check — Post Phase 1 Re-check

*Re-check after Phase 1 design.*

| Principle | Status | Design Evidence |
|---|---|---|
| I. Layered Architecture | PASS | Source tree confirms no repository imports in api/; no HTTPException in services/; domain models in domain/models.py are pure Pydantic, never SQLAlchemy |
| II. Infrastructure Contracts | PASS | infra/vault.py called in app startup event; docker-compose migrate service with depends_on condition confirmed in contracts |
| III. Streaming Runtime | PASS | chat.py and exams.py routers return StreamingResponse; redis_client.py SESSION_TTL and GUARDRAILS_TTL constants used at every SET call |
| IV. Error Boundaries | PASS | ActiveSessionExists (FR-024), AIServiceUnavailable (FR-026) added to domain/exceptions.py; all map to HTTP 4xx/503 in api/exceptions.py |
| V. Security | PASS (1 documented exception) | All Pydantic request models defined in contracts; no raw dict passes service boundary. Exception: the `guardrails-service` container receives `ANTHROPIC_API_KEY` via Compose env, not Vault — it has no runtime Vault dependency (see Guardrails design note above) |
