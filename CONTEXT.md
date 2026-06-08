# Project Context — Lebanese Math Coach

## What's built vs. what's not

### Backend — fully built (branch 002-textbook-rag)

| Feature | Files | Status |
|---|---|---|
| Exam generation (streaming) | `services/exam_service.py`, `api/routers/exams.py` | Done |
| Dual-evaluator grading (streaming) | `services/grading_service.py`, `api/routers/grading.py` | Done |
| Past question retrieval | `services/retrieval_service.py`, `api/routers/questions.py` | Done |
| Topic frequency analytics | `services/topic_service.py`, `api/routers/topics.py` | Done |
| Curriculum-scoped chat + guardrails | `services/chat_service.py`, `api/routers/chat.py` | Done |
| JWT auth | `infra/auth.py`, `api/routers/auth.py` | Done |
| Textbook page lookup | `repositories/textbook_repo.py`, `api/routers/textbook.py` | Done |
| Textbook semantic search | `services/retrieval_service.py`, `repositories/chunk_repo.py` | Done |
| Textbook ingestion CLI | `ingestion/textbook_pipeline.py` | Done |
| NeMo Guardrails sidecar | `guardrails-service/` (Docker) | Done |
| All DB migrations | `alembic/versions/0001_baseline.py`, `0002_textbook.py` | Done |

### Backend — not yet built

| Feature | Notes |
|---|---|
| Past exam ingestion pipeline | No `ingestion/pipeline.py` yet — textbook pipeline exists but no Apelr PDF ingester |
| MinIO usage | Client is wired in compose but not called by runtime code |
| Actual past exam data | No PDFs ingested — `chunks` and `topic_stats` tables are empty |

### Frontend — partially built

| Page | Status |
|---|---|
| Dashboard | Implemented with real UI components |
| Practice Exam | `ComingSoon` stub |
| Past Questions | `ComingSoon` stub |
| Topics | `ComingSoon` stub |
| Chat | `ComingSoon` stub |
| History | `ComingSoon` stub |
| Results | `ComingSoon` stub |

Auth not wired — `frontend/src/data/mock.ts` uses a hardcoded student fixture. No API calls made from the frontend yet.

---

## Remaining work (priority order)

### 1. Frontend pages (highest value)

Each page has a complete backend API to wire against.

**Chat page** — wire `POST /chat` SSE stream; render streaming tokens; handle `guardrail_warning` / `guardrail_block` events; display textbook citations when `textbook_page` / `textbook_sections` events arrive. Use KaTeX (`lib/math.tsx`) for math rendering.

**Exam page** — call `POST /exams/generate` (SSE stream of tokens); display the 4-exercise exam with KaTeX; per-part answer inputs; submit via `POST /exams/{session_id}/submit` (SSE stream); redirect to Results page.

**Results page** — fetch `GET /exams/{session_id}/results`; display strict vs. lenient scores side-by-side; highlight discrepancies.

**Topics page** — fetch `GET /topics`; render frequency table with red/yellow/green tiers (≥7, 4–6, ≤3 appearances); click topic → filter to questions.

**Past Questions page** — search form posting to `POST /questions/retrieve`; display ranked results with year/session/marks/answer.

**History page** — fetch `GET /exams/history`; list past sessions with score ranges.

### 2. Auth wiring (required before shipping)

Replace the mock student fixture in `data/mock.ts` with a real login flow. `POST /auth/jwt/login`, `POST /auth/register`, store JWT in localStorage, attach as `Authorization: Bearer <token>` on all API calls.

### 3. Past exam ingestion pipeline

Write `ingestion/pipeline.py` to ingest Apelr PDFs:
- Download from Apelr or read from `Math_GS_Exams_English/`
- Extract text with pdfplumber
- Chunk (500–800 token fixed + 100 overlap)
- Tag with haiku: topic + subtopic + question_type from predefined list
- Embed with voyage-large-2
- Insert into `chunks` table with `source_type = 'past_exam'` or `'answer_key'`
- Update `topic_stats`

Filename convention: `GS_Math_{year}_{session}_En.pdf` → past_exam; `GS_Math_{year}_{session}_En_AK.pdf` → answer_key.

---

## API contract summary

| Endpoint | Auth | Returns |
|---|---|---|
| `POST /auth/register` | none | user |
| `POST /auth/jwt/login` | none | JWT token |
| `POST /exams/generate` | Bearer | SSE: `session_created`, `token`, `exam_complete`, `[DONE]` |
| `GET /exams/{session_id}` | Bearer | ExamSession JSON |
| `GET /exams/history` | Bearer | list of ExamSession |
| `POST /exams/{session_id}/submit` | Bearer | SSE: `evaluating`, `evaluator_1_complete`, `evaluator_2_complete`, `grading_complete`, `[DONE]` |
| `GET /exams/{session_id}/results` | Bearer | EvaluationResult JSON |
| `POST /questions/retrieve` | Bearer | list of PastQuestion |
| `GET /topics` | Bearer | list of TopicStat |
| `POST /chat` | Bearer | SSE: `conversation_id`, `token`, `textbook_page`, `textbook_sections`, `guardrail_warning`, `guardrail_block`, `done`, `[DONE]` |
| `GET /textbook/page/{n}` | Bearer | TextbookPage JSON |
| `GET /health` | none | `{"status": "ok"}` |

---

## Dev workflow

```bash
# Start all services
docker compose up

# Run migrations only
docker compose run --rm migrate

# Ingest textbook (textbook/ dir must have .md files)
uv run python -m ingestion.textbook_pipeline \
  --textbook-dir textbook/ \
  --db-url postgresql://postgres:devpassword@localhost:5432/lebanese_math \
  --anthropic-key $ANTHROPIC_API_KEY \
  --voyage-key $VOYAGE_API_KEY

# Frontend dev server (not in compose)
cd frontend && npm run dev
```

## Required env vars (`.env` at repo root)

```
VAULT_TOKEN=<vault-dev-root-token>
VAULT_ADDR=http://localhost:8200
ANTHROPIC_API_KEY=<key>
VOYAGE_API_KEY=<key>
JWT_SECRET=<secret>
```

Vault seed script at `scripts/seed_vault.sh` writes these into Vault under `secret/lebanese-math-coach`.
