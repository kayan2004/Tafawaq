# Lebanese GS Math Coach — Project Context

## What this is

A web app for Lebanese Grade 12 General Sciences students to prepare for the official Baccalaureate Mathematics exam. Students can generate AI-powered mock exams, submit answers for dual AI grading, ask a curriculum-scoped tutor, and browse official past exams and the official textbook.

---

## Tech Stack

| Layer | Choice |
|---|---|
| Backend | Python 3.12, FastAPI, async throughout |
| Database | PostgreSQL 16 + pgvector extension (cosine similarity search) |
| ORM | SQLAlchemy 2.0 async (except pgvector queries, which use raw asyncpg) |
| Secrets | HashiCorp Vault KV v2 — app refuses to boot without it |
| Cache | Redis 7 — session TTL and guardrails counters |
| Object storage | MinIO — stores PDF files (textbook, official exams) |
| Auth | fastapi-users 13 + JWT (Bearer tokens) |
| LLM | claude-sonnet-4-5 for generation, grading, and chat |
| LLM (ingestion only) | claude-haiku-4-5-20251001 for tagging textbook chunks |
| Embeddings | voyage-large-2 (1536 dimensions) via Voyage AI SDK |
| Guardrails | NeMo Guardrails sidecar at http://guardrails:8100 |
| Frontend | React + Vite + TypeScript, hash-based routing (no react-router) |
| Containers | Docker Compose — single `docker compose up` starts everything |
| Migrations | Alembic — runs automatically before the API boots |

---

## Architecture Overview

```
Browser (React SPA)
       │  JWT Bearer + JSON/SSE
       ▼
  Nginx (reverse proxy)
       │
       ▼
  FastAPI backend
  ├── /auth/**           fastapi-users (register, login, /me)
  ├── /chat              SSE stream — AI coach with tools
  ├── /exams/**          generate (SSE), list sessions, get session, get results
  ├── /grade             submit answers → dual evaluator → graded results
  ├── /official-exams/** list, PDF, take (creates a user session from official exam)
  ├── /textbook/**       pages list, page by number, PDF blob
  ├── /questions/**      semantic search (pgvector)
  ├── /topics/**         frequency analytics
  └── /health
       │
  ├── PostgreSQL (exam sessions, results, messages, users, chunks, textbook_pages, topic_stats)
  ├── Redis (guardrails counter, session answer-key cache)
  └── MinIO (PDF storage: official exam PDFs, textbook PDF)
```

### Layer rules (strictly enforced)
- ORM models never leave `repositories/` — services receive Pydantic domain models
- HTTP errors (`HTTPException`) only in `api/exceptions.py` — services raise domain exceptions
- Vault is the only secrets source at runtime — no `os.environ` for secrets in services
- `embed_text()` and `call_claude()` are sync — always called via `asyncio.to_thread()`
- Streaming responses must validate before the `StreamingResponse` is returned, since exceptions inside a generator can't map to 4xx once headers are sent

---

## Database Schema

| Table | Key columns | Purpose |
|---|---|---|
| `users` | fastapi-users base + created_at, last_login | Auth |
| `conversations` | user_id FK | Chat thread identity |
| `messages` | conversation_id FK, role, guardrails_score | Chat history |
| `exam_sessions` | user_id, session_type, exam_content JSONB, answer_key JSONB, status, expires_at | One row per exam attempt (TTL: 3h) |
| `exam_results` | session_id, evaluator_1/2 JSONB, total_score_1/2, discrepancy_flagged | Permanent grading record |
| `chunks` | source_type, embedding vector(1536), year/session/exercise_id (nullable), page_start/page_end (nullable) | Shared pgvector store for past exam chunks AND textbook chunks |
| `textbook_pages` | page_number (unique), chapter, section, page_type, content | Full raw page content — supports exact page lookup by number |
| `topic_stats` | topic (unique), appearances, last_seen_year | Zero-LLM frequency analytics |

`exam_sessions.session_type` is either `mock_generated` (AI-generated exam) or `official` (student takes a shared official exam).

`exam_sessions.status` state machine: `in_progress` → `submitted` → `graded`.

---

## What Is Fully Implemented

### Backend

**Auth**
- Register, login, JWT tokens, `/auth/me`
- Admin flag (`is_superuser`) — admins see AI tool-call details in chat UI

**Exam Generation** (`POST /exams/generate`)
- SSE stream: emits `session_created` → (generation) → `exam_complete` → `[DONE]`
- Claude generates a 4-exercise, 20-point mock exam in structured JSON with LaTeX
- Weighted toward student's weak topics (currently using curriculum weighting, topic_stats not yet wired to generation)
- Exam content stored in JSONB; answer key stored separately in JSONB + Redis
- Archives any existing in-progress session before creating a new one

**Grading** (`POST /grade`)
- Two independent Claude evaluators (strict persona + lenient persona) run in parallel via `asyncio.gather`
- Each returns per-part scores, feedback, corrections
- Discrepancy flagged if evaluators differ by ≥ 2 points
- Results stored permanently in `exam_results`

**Official Exams** (`/official-exams/**`)
- Admin can upload official past exams (with PDF and structured exam content)
- Students can browse, view PDF preview, and "take" an official exam (creates a user session from it)
- Same grading pipeline as mock exams

**Chat** (`POST /chat` — SSE stream)
- Streams tokens to client in real time
- Two active tools:
  - `retrieve_textbook_page(page_number)` — fetches a specific textbook page by number from `textbook_pages`
  - `retrieve_textbook_sections(query, source_types, limit)` — semantic search via pgvector cosine similarity
- Tool-call loop runs up to 4 iterations to handle multi-step retrieval
- Guardrails: NeMo sidecar classifies off-topic messages; 3-tier system:
  - Tier 0–1: normal
  - Tier 2: warning suffix appended to response
  - Tier 3+: message blocked, stream ends
- Messages < 10 words skip NeMo classification (performance optimization)
- Full conversation history (last 20 messages) sent to Claude on each turn
- SSE event types: `conversation_id`, `token`, `tool_use` (admin only), `textbook_page`, `textbook_sections`, `guardrail_warning`, `guardrail_block`, `done`

**Textbook RAG**
- `textbook_pages` table: 236 pages from "Building Up Mathematics — Algebra and Geometry" (Grade 12 official Lebanese textbook)
- Pages ingested via `ingestion/book_ingest.py` from a Markdown file in `===PAGE N=== / ===END PAGE N===` format
- A separate chunked+embedded pipeline (`ingestion/textbook_pipeline.py`) exists for semantic search (reads YAML-frontmatter markdown)
- The chat tool `retrieve_textbook_sections` does pgvector cosine search across chunks

**Session management**
- `GET /exams/sessions` — paginated history
- `GET /exams/{session_id}` — full session with exam content
- `GET /exams/{session_id}/results` — graded results with corrections
- `GET /exams/active` — active in-progress session

### Frontend

**Auth flow**
- Login / register page — real API calls, JWT stored in `localStorage`
- Token expiry handled — SESSION_EXPIRED throws, user redirected to login

**Chat page** (fully implemented)
- Real-time SSE token streaming, renders LaTeX via KaTeX
- Tool-call chips displayed (admin mode shows tool name + input JSON)
- Guardrail warning/block UI
- New chat / sign out
- `/generate` slash command: shows a local response in chat ("I've queued a new mock exam..."), sets a flag in App state; when user navigates to Exams tab, generation auto-starts
- Unknown slash commands show `Unknown command: /foo` locally — never reach the API

**Exam page** (fully implemented)
- Browse view: lists official exams and mock exam history
- Generate: `+ Generate New Exam` button (or via `/generate` in chat) — SSE stream, live skeleton while generating
- Taking view:
  - Exercise tab bar (I, II, III, IV)
  - Stem + parts rendered with KaTeX
  - Per-part answer textareas
  - Desmos graphing calculator panel (JS API, slide-in)
  - Official exam: "View PDF" button opens PDF in new tab
  - Submit with confirmation dialog
- Results / corrections view:
  - Strict / Average / Lenient scores
  - Per-part: student answer, evaluator note, full correction with LaTeX
  - Discrepancy flag if evaluators disagreed
  - Export PDF (window.print())
- Resume: in-progress sessions can be continued

**Books page** (implemented)
- Library card for "Mathematics Grade 12 — Algebra & Geometry"
- Fetches PDF blob from MinIO via `/textbook/pdf/{filename}`, renders in an iframe
- (PDF must be uploaded to MinIO separately — the page content is in `textbook_pages` already)

**Dashboard** (partially implemented)
- Shows welcome, streak, stat tiles, topic frequency summary, recent attempts
- Data is currently hardcoded mock data — not wired to API yet

### Slash command system in chat
- Intercepts `/command` before hitting the API
- `/generate` → queues exam generation, shows confirmation message
- Unknown commands → shows error message locally
- Designed to be extensible (more commands can be added)

---

## What Is NOT Implemented (Stubs / TODO)

| Feature | Status |
|---|---|
| Past Questions page | `ComingSoon` stub — backend (`/questions/**`) exists and works, frontend not built |
| Topics page | `ComingSoon` stub — backend (`/topics/**`) exists, frontend not built |
| History/Results page (dedicated) | `ComingSoon` stub — results accessible via the Exams page instead |
| Dashboard real data | Hardcoded mock data — not wired to API |
| Topic-weighted exam generation | Curriculum weighting hardcoded — `topic_stats` not yet read to bias generation |
| Textbook semantic search (full pipeline) | `ingestion/textbook_pipeline.py` exists but hasn't been run — chunks table is empty for textbook; `retrieve_textbook_sections` tool works but returns nothing until the pipeline runs |
| MinIO textbook PDF upload | Books page UI exists; PDF must be manually uploaded to MinIO |
| Auth on frontend — user profile | `getMe()` fetches `is_superuser` only; name/email not displayed (mock `STUDENT` object used) |
| Past exam ingestion pipeline | Spec 001 describes it; not yet written — `chunks` table has no past exam data |

---

## Key User Flows

### Flow 1: Generate and take a mock exam
1. User logs in
2. Navigates to Exams tab (or types `/generate` in Chat)
3. Clicks "+ Generate New Exam" → SSE stream starts
4. Loading skeleton shown (~30 seconds while Claude generates)
5. Exam appears: 4 exercises, LaTeX-rendered, with answer textareas
6. User can open Desmos calculator alongside
7. User clicks Submit → confirmation dialog → grading begins (~15–20 seconds)
8. Results page: strict/average/lenient scores, per-part feedback and full corrections

### Flow 2: Take an official past exam
1. User browses Official Exams section
2. Clicks "View" → detail page with embedded PDF preview
3. Clicks "Start Exam" → session created from official exam content
4. Same taking/submission/grading flow as mock exam

### Flow 3: Ask the AI tutor
1. User goes to Chat tab
2. Types a math question
3. Response streams token by token with KaTeX rendering
4. If question requires textbook lookup, Claude calls `retrieve_textbook_page(N)` or `retrieve_textbook_sections(query)`
5. Frontend shows a "textbook_page" event chip with page metadata
6. Claude answers using retrieved content

### Flow 4: Look up a textbook page
1. User types e.g. "explain what's on page 45 of the textbook"
2. Claude calls `retrieve_textbook_page(45)` tool
3. Backend fetches from `textbook_pages` where `page_number = 45`
4. Claude receives the raw OCR-converted page content and answers the question

---

## Ingestion Pipelines

### Textbook pages (implemented & run)
- Script: `ingestion/book_ingest.py`
- Input: `textbook/building_up_mathematics_1.md` (PDF → Markdown conversion, `===PAGE N===` format)
- Output: 236 rows in `textbook_pages`
- Run: `uv run python -m ingestion.book_ingest`

### Textbook semantic chunks (pipeline built, not run)
- Script: `ingestion/textbook_pipeline.py`
- Input: Markdown files with YAML frontmatter (`page`, `chapter`, `section`, `type`) separated by `===PAGE_BREAK===`
- Process: parse → chunk by section → tag with claude-haiku → embed with voyage-large-2 → insert into `chunks` with pgvector
- Output: rows in `chunks` with `source_type = textbook_*` and 1536d embeddings

### Past exam chunks (not yet built)
- Spec exists (`specs/001-lebanese-math-coach/`)
- Would populate `chunks` with `source_type = past_exam` / `answer_key`
- Tools for past exam retrieval exist in `infra/llm/tools.py` but are not active in chat yet

---

## Models in Use

| Task | Model |
|---|---|
| Exam generation | claude-sonnet-4-5 |
| Dual grading (both evaluators) | claude-sonnet-4-5 |
| Chat tutor | claude-sonnet-4-5 |
| Textbook chunk tagging (ingestion only) | claude-haiku-4-5-20251001 |
| Embeddings | voyage-large-2 (1536d) |

---

## Known Constraints / Design Decisions

- **Validator disabled**: A background exam-validation pipeline was built (two-step: student-persona solver + judge comparator) but disabled after testing showed too many false negatives from an overly strict judge. The infrastructure is preserved in `exam_service.py` for future tuning.
- **Hash routing**: No react-router-dom — navigation is `window.location.hash` + state. All page components are conditionally rendered in `App.tsx`.
- **SSE over WebSockets**: Both generation and chat use Server-Sent Events (one-directional streaming from server). Frontend uses `ReadableStreamDefaultReader` to parse SSE frames.
- **Answer key in Redis**: At grading time, the answer key is read from Redis (set at generation time) to avoid re-querying the DB for the fast-path. DB is the source of truth.
- **Router registration order is load-bearing**: grading router must be registered before exams router in `main.py`, or `GET /exams/history` is shadowed by `GET /exams/{session_id}`.
- **pgvector via raw asyncpg**: SQLAlchemy cannot express the `<=>` operator without custom types. All vector similarity queries bypass the ORM entirely.
