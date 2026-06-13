# Project Context — Lebanese Math Coach (Tafawwaq)

## What this is

Lebanese GS Grade 12 Math exam-prep platform branded **Tafawwaq** (تفوّق — "to excel").
Students generate mock exams, submit handwritten/typed answers for dual AI grading,
browse past official Bac exams, and chat with a curriculum-scoped AI tutor.

Tech stack: FastAPI backend · PostgreSQL + pgvector · Redis · HashiCorp Vault ·
React + Vite + TypeScript frontend · Docker Compose · Claude (Anthropic) · ElevenLabs TTS.

---

## What's built — backend

All services are live in Docker Compose.

| Feature | Router | Service | Status |
|---|---|---|---|
| JWT auth (register / login) | `api/routers/auth.py` | `infra/auth.py` | ✅ Done |
| Mock exam generation (SSE) | `api/routers/exams.py` | `services/exam_service.py` | ✅ Done |
| Dual-evaluator grading (SSE) | `api/routers/grading.py` | `services/grading_service.py` | ✅ Done |
| Official Bac exam browser | `api/routers/official_exams.py` | `services/official_exam_service.py` | ✅ Done |
| Handwritten answer extraction | `api/routers/exams.py` → `POST /exams/extract-answers` | Claude Vision | ✅ Done |
| Curriculum-scoped chat + guardrails | `api/routers/chat.py` | `services/chat_service.py` | ✅ Done |
| Past question retrieval (pgvector) | `api/routers/questions.py` | `services/retrieval_service.py` | ✅ Done |
| Topic frequency analytics | `api/routers/topics.py` | `services/topic_service.py` | ✅ Done |
| Textbook page lookup | `api/routers/textbook.py` | `repositories/textbook_repo.py` | ✅ Done |
| Textbook semantic search | embedded in chat tools | `repositories/chunk_repo.py` | ✅ Done |
| TTS proxy (ElevenLabs) | `api/routers/tts.py` | `services/tts_service.py` | ✅ Done |
| User details / onboarding | `api/routers/user_details.py` | `repositories/user_details_repo.py` | ✅ Done |
| NeMo Guardrails sidecar | `guardrails-service/` (Docker) | — | ✅ Done |
| Textbook ingestion CLI | `ingestion/textbook_pipeline.py` | — | ✅ Done |

### Backend — not yet built

| Feature | Notes |
|---|---|
| Past exam ingestion pipeline | No `ingestion/pipeline.py` yet — raw PDFs in `Math_GS_Exams_English/` but not ingested |
| MinIO usage | Client wired in compose, not called by runtime code |
| `chunks` / `topic_stats` data | Tables exist but are empty — no past exam data ingested yet |

---

## What's built — frontend

All pages have real implementations except Past Questions and Topics.

| Page | Route (`#`) | Status | Notes |
|---|---|---|---|
| Login | — | ✅ Done | Real JWT auth; register + login form |
| Onboarding | — | ✅ Done | Collects grade, goal, weak topics on first login; gates the app |
| Dashboard | `#dashboard` | ✅ Done | Stats cards, recent exams, quick-start |
| Exam | `#exam` | ✅ Done | Mock generation (SSE) + Official Bac browser; answer entry; handwritten image upload (Claude Vision); dual grading with score display; Desmos graphing calculator |
| Chat | `#chat` | ✅ Done | Streaming SSE chat; KaTeX math rendering; TTS read-aloud (ElevenLabs); persistent history across sessions; `/exam` command to attach an exam session as context; TafawwaqMascot animated character in header |
| Books | `#books` | ✅ Done | In-browser PDF viewer for ingested textbooks |
| Past Questions | `#past` | ❌ Stub | Backend ready (`POST /questions/retrieve`); UI not built |
| Topics | `#topics` | ❌ Stub | Backend ready (`GET /topics`); UI not built |
| Results | (embedded in Exam) | ✅ Done | Shown inline on the Exam page after grading |

### Auth
Real JWT flow — `POST /auth/jwt/login`, token stored in localStorage, attached as
`Authorization: Bearer <token>` on all API calls. Mock fixture in `data/mock.ts` is
still used for the sidebar user card display but not for auth.

### TafawwaqMascot
SVG animated character (`frontend/TafawwaqMascot.jsx`) mounted in the chat header.

| State | Trigger |
|---|---|
| `thinking` | SSE stream open (tokens arriving) |
| `talking` | ElevenLabs audio playing |
| `nailed` | Assistant response contains a score ≥ 14/20 (fires for 1.8 s, auto-returns to idle) |
| `idle` | Default |

Mouth is driven by a Web Audio `AnalyserNode` rAF loop — `mouthOpen` when loudness > 28.

---

## Full API contract

| Endpoint | Auth | Description |
|---|---|---|
| `POST /auth/register` | none | Create account |
| `POST /auth/jwt/login` | none | Returns JWT |
| `GET /auth/me` | Bearer | Current user info (`is_superuser` flag) |
| `POST /exams/generate` | Bearer | SSE stream: `session_created`, `token`, `exam_complete`, `[DONE]` |
| `GET /exams/{session_id}` | Bearer | Full exam session JSON |
| `GET /exams/history` | Bearer | List of exam session summaries |
| `POST /exams/{session_id}/submit` | Bearer | SSE stream: `evaluating`, `evaluator_1_complete`, `evaluator_2_complete`, `grading_complete`, `[DONE]` |
| `GET /exams/{session_id}/results` | Bearer | Dual-evaluator result JSON |
| `POST /exams/extract-answers` | Bearer | Multipart image → Claude Vision → extracted answer text |
| `GET /official-exams` | Bearer | List of official Bac exams (year, session, PDF URL) |
| `POST /official-exams/{exam_id}/take` | Bearer | Creates an exam session from an official exam |
| `GET /official-exams/{exam_id}/pdf` | Bearer | Signed PDF URL |
| `POST /questions/retrieve` | Bearer | pgvector similarity search → list of past questions |
| `GET /topics` | Bearer | Topic frequency stats |
| `POST /chat` | Bearer | SSE stream: `conversation_id`, `token`, `tool_use`, `textbook_page`, `textbook_sections`, `guardrail_warning`, `guardrail_block`, `done`, `[DONE]` |
| `GET /chat/history` | Bearer | Persisted message history for current conversation |
| `DELETE /chat/history` | Bearer | Clear conversation history |
| `GET /textbook/page/{n}` | Bearer | Single textbook page JSON |
| `POST /tts` | Bearer | Text → ElevenLabs audio blob (mp3) |
| `GET /user-details` | Bearer | Onboarding profile (`null` if not yet completed) |
| `POST /user-details` | Bearer | Save onboarding answers |
| `GET /health` | none | `{"status": "ok"}` |

---

## Database tables

| Table | Key columns | Notes |
|---|---|---|
| `users` | fastapi-users base + `created_at`, `last_login` | |
| `user_details` | `user_id` FK, `grade`, `goal`, `weak_topics` (array) | Populated by onboarding |
| `conversations` | `user_id` FK | One active conversation per user |
| `messages` | `conversation_id` FK, `role` enum, `guardrails_score` nullable | Persisted chat history |
| `exam_sessions` | `user_id`, `session_type` (`mock_generated` \| `official`), `exam_content` JSONB, `answer_key` JSONB, `status`, `expires_at` | TTL = 3 hours |
| `exam_results` | `session_id`, `evaluator_1/2` JSONB, `total_score_1/2`, `discrepancy_flagged` | Permanent |
| `chunks` | `source_type`, `embedding vector(1536)`, `year/session/exercise_id` nullable, `page_start/page_end` nullable | Shared for past_exam + answer_key + textbook chunks |
| `textbook_pages` | `page_number` (unique), `chapter`, `section`, `page_type`, `content` | Raw page store |
| `topic_stats` | `topic` (unique), `appearances`, `last_seen_year` | Zero-LLM analytics |

---

## LLM / model config (locked)

| Task | Model |
|---|---|
| Exam generation | `claude-sonnet-4-5` |
| Dual grading (both evaluators) | `claude-sonnet-4-5` |
| Chat | `claude-sonnet-4-5` |
| Handwritten answer extraction | `claude-sonnet-4-5` (Vision) |
| Textbook tagging (ingestion only) | `claude-haiku-4-5-20251001` |
| Embeddings | `voyage-large-2` (1536d) |
| TTS | ElevenLabs (proxied via `/tts`) |

---

## Remaining work (priority order)

### 1. Past exam ingestion pipeline
Write `ingestion/pipeline.py` to process PDFs in `Math_GS_Exams_English/`:
- Extract text with pdfplumber
- Chunk (500–800 token fixed + 100 overlap)
- Tag with haiku: topic, subtopic, question_type
- Embed with voyage-large-2, insert into `chunks` table (`source_type = 'past_exam'` or `'answer_key'`)
- Update `topic_stats`

Filename convention: `GS_Math_{year}_{session}_En.pdf` → past_exam; `_AK.pdf` → answer_key.

### 2. Past Questions page (`#past`)
Wire `POST /questions/retrieve` — search form, ranked results with year/session/marks/answer.

### 3. Topics page (`#topics`)
Wire `GET /topics` — frequency table with red/yellow/green tiers (≥7, 4–6, ≤3 appearances).

### 4. Nailed state from grading service
Currently `nailed` on the mascot only fires when the chat AI mentions a score ≥ 14/20 in text.
A richer trigger would fire it from the actual grading SSE result on the Exam page
(when `(total_score_1 + total_score_2) / 2 ≥ 14`).

---

## Dev workflow

```bash
# Start everything
docker compose up

# Rebuild a single service after code changes
docker compose up --build frontend -d

# Run migrations only
docker compose run --rm migrate

# Ingest textbook (textbook/ dir must contain .md files with YAML frontmatter)
uv run python -m ingestion.textbook_pipeline \
  --textbook-dir textbook/ \
  --db-url postgresql://postgres:devpassword@localhost:5432/lebanese_math \
  --anthropic-key $ANTHROPIC_API_KEY \
  --voyage-key $VOYAGE_API_KEY

# Frontend hot-reload dev server (outside Docker)
cd frontend && npm run dev
```

## Required secrets (written to Vault by `scripts/seed_vault.sh`)

```
ANTHROPIC_API_KEY     — Claude API
VOYAGE_API_KEY        — voyage-large-2 embeddings
JWT_SECRET            — fastapi-users JWT signing
ELEVENLABS_API_KEY    — TTS proxy (optional — returns 503 if missing, rest of app unaffected)
DATABASE_URL          — postgresql+asyncpg://...
REDIS_URL             — redis://...
```

Vault address: `http://localhost:8200` (dev mode, root token in `.env`).
All secrets live under `secret/lebanese-math-coach` (KV v2).
