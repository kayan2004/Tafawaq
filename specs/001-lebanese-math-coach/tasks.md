---
description: "Task list for Lebanese Math Coach — Phase 1: Infrastructure Foundation + Phase 2: Ingestion Pipeline"
---

# Tasks: Lebanese Math Coach — Phase 1 + Phase 2

**Input**: Design documents from `specs/001-lebanese-math-coach/`

**Prerequisites**: plan.md ✅ | spec.md ✅ | research.md ✅ | data-model.md ✅

**Tests**: Not requested — no test tasks generated.

---

## Plan Phase 1 — Infrastructure Foundation: Setup (Project Scaffolding)

**Purpose**: Create the repository skeleton, Docker config, and dependency manifests so every
developer and CI environment starts from the same structure.

- [X] T001 Create the full app/ directory structure per plan.md: app/api/routers/, app/api/, app/services/, app/repositories/, app/domain/, app/infra/llm/, app/infra/embeddings/, app/data/few_shot_exams/ (empty __init__.py in each Python package)
- [X] T002 [P] Create ingestion/ directory structure with empty __init__.py files: ingestion/pipeline.py, ingestion/pdf_extractor.py, ingestion/chunker.py, ingestion/tagger.py, ingestion/embedder.py (stub files with module docstrings only — implementation in Plan Phase 2)
- [X] T003 [P] Create pyproject.toml at repo root with all backend dependencies: fastapi==0.115.*, sqlalchemy[asyncio]==2.0.*, fastapi-users[sqlalchemy]==13.*, anthropic, voyageai, redis[hiredis]>=5, minio, hvac, pdfplumber, pgvector, alembic, asyncpg, uvicorn[standard], pydantic>=2, pytest, pytest-asyncio
- [X] T004 [P] Create frontend/ scaffold: run `npm create vite@latest frontend -- --template react-ts`, then install dependencies: katex, @types/katex, tailwindcss, postcss, autoprefixer; init Tailwind config
- [X] T005 [P] Create frontend/vite.config.ts with dev proxy — proxy all requests `/*` to http://localhost:8000 (backend routes have no /api/ prefix per contracts; do NOT restrict proxy to /api/* only)
- [X] T006 [P] Create .env.example at repo root with exactly two entries: VAULT_ADDR=http://vault:8200 and VAULT_TOKEN=dev-root-token; add .env to .gitignore
- [X] T007 Create Dockerfile for api service: FROM python:3.12-slim, COPY uv binary from ghcr.io/astral-sh/uv:latest, COPY pyproject.toml, RUN uv pip install --system . (uv cache mount), COPY app/ app/, CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
- [X] T008 Create docker-compose.yml with all 7 services — full spec below. (NOTE: two more services were added after Phase 1 — `pgadmin` as a dev DB browser, and `guardrails` (the NeMo microservice) added in Phase 4 per T045 — bringing the live total to 9.)
  - **db**: image pgvector/pgvector:pg16 (NOT postgres:16 — pgvector extension must be pre-installed), env POSTGRES_DB=lebanese_math POSTGRES_USER=postgres POSTGRES_PASSWORD=devpassword (dev-mode exception: DB password in compose accepted for local dev only, not a production secret), healthcheck: pg_isready -U postgres
  - **redis**: image redis:7-alpine, healthcheck: redis-cli ping
  - **minio**: image minio/minio, command server /data --console-address :9001, env MINIO_ROOT_USER=minioadmin MINIO_ROOT_PASSWORD=minioadmin, healthcheck: curl -f http://localhost:9000/minio/health/live
  - **vault**: image hashicorp/vault, cap_add: IPC_LOCK, env VAULT_DEV_ROOT_TOKEN_ID=${VAULT_TOKEN} VAULT_DEV_LISTEN_ADDRESS=0.0.0.0:8200, healthcheck: vault status -address=http://127.0.0.1:8200
  - **vault-seed**: image hashicorp/vault, one-shot container that writes all app secrets to Vault KV v2 at path secret/lebanese-math-coach; depends_on vault (healthy); env VAULT_ADDR=http://vault:8200 VAULT_TOKEN=${VAULT_TOKEN}; command: sh scripts/seed_vault.sh; restart: on-failure
  - **migrate**: build from Dockerfile, command: alembic upgrade head, depends_on db (healthy) + vault-seed (service_completed_successfully), env DATABASE_URL=postgresql+asyncpg://postgres:devpassword@db:5432/lebanese_math (passed directly — migrate does not call resolve_secrets()); restart: on-failure
  - **api**: build from Dockerfile, ports 8000:8000, depends_on db (healthy) + redis (healthy) + vault (healthy) + vault-seed (service_completed_successfully) + migrate (service_completed_successfully), env_file .env

---

## Plan Phase 1 — Infrastructure Foundation: Foundational (Blocking Prerequisites)

**Purpose**: Domain layer, infrastructure adapters, ORM models, Alembic migration, FastAPI app
wiring, auth, and health endpoint. MUST be complete before any user story phase begins.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

### Domain Layer

- [X] T009 [P] Create app/domain/enums.py with four enums: SessionType (mock_generated | real_past_exam), SessionStatus (in_progress | submitted | graded), QuestionType (proof | calculation | mcq | sketch), MessageRole (user | assistant) — all inherit from (str, Enum)
- [X] T010 [P] Create app/domain/exceptions.py with full hierarchy: base LebaneseCoachError(Exception); then ExamNotFound, AnswerKeyNotFound, TopicNotFound (→ HTTP 404); ActiveSessionExists (→ HTTP 409, include active_session_id and expires_at fields); SessionExpired (→ HTTP 410); InvalidAnswerSubmission (→ HTTP 422); AIServiceUnavailable, EmbeddingServiceUnavailable, VaultUnavailable (→ HTTP 503)
- [X] T011 Create app/domain/models.py with all Pydantic domain models per data-model.md: ExercisePart, GraphSpec, Exercise, ExamContent, ExamSession, EvaluatorScore, EvaluationResult, PastQuestion, TopicStat, ErrorResponse (fields: error: str, request_id: str); no SQLAlchemy imports permitted in this file

### Infrastructure Adapters

- [X] T012 Create app/infra/vault.py: define AppSecrets(BaseModel) with all secret fields (anthropic_api_key, voyage_api_key, db_password, db_url, minio_access_key, minio_secret_key, jwt_secret); implement resolve_secrets() — creates hvac.Client(url=VAULT_ADDR, token=VAULT_TOKEN), calls client.is_authenticated(), raises VaultUnavailable if false, reads kv secret at path "lebanese-math-coach", returns AppSecrets(**data)
- [X] T013 [P] Create app/infra/redis_client.py: define SESSION_TTL = 10_800 and GUARDRAILS_TTL = 10_800 as module-level constants with inline comments justifying the TTL; implement async helpers: set_session(redis, session_id, data: dict), get_session(redis, session_id) → dict | None, delete_session(redis, session_id), get_guardrails_counter(redis, session_id) → int, set_guardrails_counter(redis, session_id, value: int), increment_guardrails_counter(redis, session_id) → int; every redis.set() MUST pass ex=SESSION_TTL or ex=GUARDRAILS_TTL
- [X] T014 [P] Create app/infra/minio_client.py: implement get_minio_client(secrets: AppSecrets) → Minio; upload_pdf(client, bucket, filename, data: bytes); get_pdf_bytes(client, bucket, filename) → bytes; bucket name constant PAST_EXAMS_BUCKET = "past-exams"

### ORM Models

- [X] T015 Create app/repositories/orm.py with all 7 ORM models per data-model.md using SQLAlchemy 2.0 mapped_column style: UserORM extending fastapi-users BaseUser[uuid.UUID] (single source of truth for the User entity — do NOT define a separate User model elsewhere), ConversationORM, MessageORM, ExamSessionORM (status and session_type use SQLAlchemy Enum mapped to domain enums; exam_content and answer_key use JSONB), ExamResultORM (no expires_at — permanent per FR-025), ChunkORM (include exercise_id: Mapped[int] column — required for answer key pairing per research.md Decision 7), TopicStatsORM; all import from app/domain/enums.py for enum types; no Pydantic imports

### Alembic Migration

- [X] T016 Create alembic/env.py: configure async SQLAlchemy engine using DATABASE_URL constructed from Vault secrets at migration time (read from environment variable DATABASE_URL set by docker-compose migrate service); import all ORM models so autogenerate detects them; use run_async_migrations() pattern for asyncpg
- [X] T017 Create alembic/versions/0001_baseline.py: CREATE EXTENSION IF NOT EXISTS vector; CREATE TABLE for all 7 tables matching ORM definitions in T015; CREATE INDEX chunks_embedding_hnsw_idx ON chunks USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64); this migration must be reversible (downgrade drops all tables and extension)

### FastAPI App Wiring

- [X] T018 Create app/main.py: define @asynccontextmanager lifespan — calls resolve_secrets() (raises VaultUnavailable on failure → process exits), stores result in app.state.secrets, initialises redis pool in app.state.redis; add RequestIDMiddleware that generates uuid4() per request, attaches to request.state.request_id, and sets X-Request-ID response header; create FastAPI(lifespan=lifespan) app instance
- [X] T019 Create app/api/exceptions.py: register @app.exception_handler for every exception in domain/exceptions.py; each handler must return JSONResponse(status_code=<correct code>, content=ErrorResponse(error=str(exc), request_id=request.state.request_id).model_dump()); catch-all handler for Exception returns 500 with same shape; MUST NOT leak stack traces
- [X] T020 [P] Create app/api/dependencies.py: get_async_session() → AsyncSession (SQLAlchemy async sessionmaker using db_url from app.state.secrets); get_redis() → Redis (from app.state.redis); get_secrets() → AppSecrets (from app.state.secrets); current_active_user dependency via fastapi-users

### Authentication

- [X] T021 Create auth configuration in app/infra/auth.py: import UserORM from app/repositories/orm.py (do NOT define a new SQLAlchemy model here — UserORM in repositories/orm.py is the single User model); define UserCreate, UserUpdate, UserRead Pydantic schemas; implement UserManager subclass with required password validation; configure JWTStrategy(secret=app.state.secrets.jwt_secret, lifetime_seconds=86400); configure BearerTransport(tokenUrl="/auth/jwt/login"); wire FastAPIUsers(user_model=UserORM, ...) instance
- [X] T022 Create app/api/routers/auth.py: include fastapi-users auth_router (POST /auth/jwt/login, POST /auth/jwt/logout) and register_router (POST /auth/register); include users_router (GET /auth/me); register all three routers in app/main.py with prefix="" (fastapi-users handles prefixes internally)

### Health Endpoint

- [X] T023 Create app/api/routers/health.py: implement GET /health — async handler that checks (1) vault: re-authenticates hvac client, (2) db: executes SELECT 1 via get_async_session(), (3) redis: sends PING via get_redis(); returns {"status": "ok", "vault": "connected", "db": "connected", "redis": "connected"} if all pass; returns 503 with failed services listed if any check fails; register router in app/main.py

### Vault Seed Script

- [X] T025 Create scripts/seed_vault.sh: shell script that uses the vault CLI to write all application secrets to KV v2 at path secret/lebanese-math-coach; reads secret values from environment variables (ANTHROPIC_API_KEY, VOYAGE_API_KEY, MINIO_ACCESS_KEY, MINIO_SECRET_KEY, JWT_SECRET); sets defaults for dev if vars not set (e.g. JWT_SECRET=dev-jwt-secret-change-in-prod); script: `vault kv put -address=$VAULT_ADDR secret/lebanese-math-coach anthropic_api_key=$ANTHROPIC_API_KEY voyage_api_key=$VOYAGE_API_KEY db_url=postgresql+asyncpg://postgres:devpassword@db:5432/lebanese_math db_password=devpassword minio_access_key=${MINIO_ACCESS_KEY:-minioadmin} minio_secret_key=${MINIO_SECRET_KEY:-minioadmin} jwt_secret=${JWT_SECRET:-dev-jwt-secret-change-in-prod}`

### Phase 1 Checkpoint

- [X] T024 Verify Phase 1 checkpoint: run `docker-compose up -d` → confirm all 6 services healthy via `docker-compose ps`; run `docker-compose run --rm migrate` → exits 0; run `curl http://localhost:8000/health` → returns {"status": "ok", ...}; run `curl -X POST http://localhost:8000/auth/register -d '{"email":"test@test.com","password":"pass123"}'` → returns 201; run `curl -X POST http://localhost:8000/auth/jwt/login -F "username=test@test.com" -F "password=pass123"` → returns access_token

---

## Plan Phase 2 — Ingestion Pipeline

**Purpose**: Process the 20 past exam PDFs from `Math_GS_Exams_English/` into tagged, embedded
pgvector chunks. This is an offline one-shot pipeline — not a runtime API feature. Required before
any RAG feature (Phase 4+) can work.

**Pipeline flow**: local PDF dir → upload to MinIO `past-exams` bucket → pdfplumber text extract
→ exercise-level chunk → claude-haiku tag → voyage-large-2 embed → pgvector INSERT → topic_stats

**PDF source**: `Math_GS_Exams_English/` at repo root (20 files, years 2004–2024).
**Run command**: `uv run --env-file .env python -m ingestion.pipeline --pdf-dir Math_GS_Exams_English`

### Ingestion Modules

- [X] T026 [P] Implement `ingestion/pdf_extractor.py`: replace stub — implement `extract_pages(pdf_bytes: bytes) -> dict[int, str]` using pdfplumber; open via `pdfplumber.open(io.BytesIO(pdf_bytes))`; for each page call `page.extract_text()`; skip pages where result is None or whitespace-only; return dict of 1-indexed page_num → text string; no side-effects, pure function

- [X] T027 [P] Implement `ingestion/chunker.py`: replace stub — implement `chunk_pdf(pages: dict[int, str], year: int, session: int) -> list[dict]`; join all page texts; detect answer-key section by matching header regex `r"(correction|answer\s*key|solutions?)"` (case-insensitive); split on `r"Exercise\s+(\d+)"` boundaries within each section; each output dict must contain: `source_type` ("past_exam" or "answer_key"), `year` (int), `session` (int), `exercise_id` (int, from regex match), `marks` (float, parsed from first match of `r"(\d+\.?\d*)\s*p(?:oint|t)"` or 0.0 if not found), `content` (str, full exercise text); if no answer-key section is found produce only source_type="past_exam" chunks

- [X] T028 [P] Implement `ingestion/tagger.py`: replace stub — implement `tag_chunks(chunks: list[dict], api_key: str) -> list[dict]`; for each chunk call `anthropic.Anthropic(api_key=api_key).messages.create(model="claude-haiku-4-5-20251001", max_tokens=128, messages=[{"role": "user", "content": TAG_PROMPT.format(content=chunk["content"][:800])}])`; TAG_PROMPT requests JSON with exactly three keys: topic (str), subtopic (str), question_type (one of proof|calculation|mcq|sketch); parse JSON from `.content[0].text`; on JSON parse failure default to topic="Unknown", subtopic="", question_type="calculation"; populate chunk["topic"], chunk["subtopic"], chunk["question_type"]; return updated chunks list

- [X] T029 Implement `ingestion/embedder.py`: replace stub — implement `embed_batch(chunks: list[dict], api_key: str) -> list[dict]`; instantiate `voyageai.Client(api_key=api_key)`; process in batches of 16 to stay within rate limits; for each batch call `client.embed([c["content"] for c in batch], model="voyage-large-2", input_type="document")`; assign `result.embeddings[i]` (list of 1536 floats) to `batch[i]["embedding"]`; return all chunks with embedding field populated

- [X] T030 Implement `ingestion/pipeline.py`: replace stub — implement full orchestration with three functions and a CLI entry:
  - `filename_to_meta(name: str) -> tuple[int, int]`: parse year and session from filename pattern `Math_GS_English_{YEAR}_Session{N}.pdf` or `Math_GS_English_{YEAR}_Exceptional.pdf` using regex; return (year, session) where session=0 for Exceptional
  - `upload_pdfs(pdf_dir: str, minio_client) -> list[str]`: iterate `*.pdf` files in pdf_dir sorted; for each, check if object already exists in MinIO `past-exams` bucket (catch S3Error); upload via `minio_client.put_object("past-exams", filename, BytesIO(data), len(data))`; return list of uploaded filenames; log each upload
  - `async run_pipeline(pdf_dir, db_url, anthropic_key, voyage_key, minio_url, minio_access, minio_secret)`: create MinIO `Minio(minio_url.replace("http://",""), access_key=minio_access, secret_key=minio_secret, secure=False)` client; ensure `past-exams` bucket exists via `make_bucket` (catch BucketAlreadyOwnedByYou); call `upload_pdfs`; for each PDF object listed in bucket: download via `get_object`, call `extract_pages()`, call `chunk_pdf(pages, year, session)` using `filename_to_meta`; accumulate all chunks; call `tag_chunks(all_chunks, anthropic_key)`; call `embed_batch(tagged_chunks, voyage_key)`; connect via `asyncpg.connect(db_url)`; bulk insert into `chunks` via executemany with `INSERT INTO chunks (id, source_type, year, session, exercise_id, topic, subtopic, question_type, marks, content, embedding) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11) ON CONFLICT DO NOTHING`; compute topic_stats via `INSERT INTO topic_stats (id, topic, subtopic, appearances, last_seen_year, last_seen_session) SELECT gen_random_uuid(), topic, MAX(subtopic), COUNT(*), MAX(year), MAX(session) FROM chunks WHERE source_type='past_exam' GROUP BY topic ON CONFLICT (topic) DO UPDATE SET appearances=EXCLUDED.appearances, last_seen_year=EXCLUDED.last_seen_year, last_seen_session=EXCLUDED.last_seen_session`; log total chunks inserted and topic_stats rows
  - CLI block: `if __name__ == "__main__"` — argparse with flags `--pdf-dir` (default "Math_GS_Exams_English"), `--db-url` (default `os.getenv("DATABASE_URL")`), `--anthropic-key` (default `os.getenv("ANTHROPIC_API_KEY")`), `--voyage-key` (default `os.getenv("VOYAGE_API_KEY")`), `--minio-url` (default "http://localhost:9000"), `--minio-access` (default "minioadmin"), `--minio-secret` (default "minioadmin"); call `asyncio.run(run_pipeline(...))`
  - **pgvector registration**: immediately after `asyncpg.connect(db_url)`, call `await pgvector.asyncpg.register_vector(conn)` before any INSERT — without this asyncpg cannot serialize Python `list[float]` to the `vector` column type and will raise a codec error

### Phase 2 Checkpoint

- [X] T031 Verify Phase 2 checkpoint: ensure Docker stack is running (`docker compose up -d db minio`); run `uv run --env-file .env python -m ingestion.pipeline --pdf-dir Math_GS_Exams_English`; verify via `docker compose exec db psql -U postgres lebanese_math -c "SELECT COUNT(*) FROM chunks"` → 100+ rows; verify `docker compose exec db psql -U postgres lebanese_math -c "SELECT COUNT(*) FROM topic_stats"` → ~12 rows; verify at least one chunk has a non-null embedding vector

---

## Plan Phase 3 — RAG Retrieval + Topic Analytics

**Purpose**: Expose the ingested chunks to the API via pgvector cosine similarity search (US3)
and pure-SQL topic frequency analytics (US4). Both depend on Phase 2 ingestion completing first.
All Phase 3 endpoints return standard JSON — no streaming.

**API surface**: `POST /questions/retrieve` (US3), `GET /topics/stats` (US4),
`GET /topics/{topic}/questions` (US4).

### US3 — Past Question Retrieval

- [X] T032 [P] [US3] Implement app/infra/embeddings/voyage.py: define embed_text(text: str, api_key: str) → list[float] using voyageai.Client(api_key=api_key).embed([text], model="voyage-large-2", input_type="query"); wrap voyageai.APIError in EmbeddingServiceUnavailable from app/domain/exceptions.py; also define embed_batch(texts: list[str], api_key: str) → list[list[float]] with input_type="document" for future ingestion use

- [X] T033 [P] [US3] Implement app/repositories/chunk_repo.py: use asyncpg.Connection directly (not SQLAlchemy — pgvector <=> operator works cleanly with asyncpg); implement cosine_similarity_search(conn: asyncpg.Connection, embedding: list[float], topic: str | None, question_type: str | None, year_from: int | None, year_to: int | None, limit: int = 10) → list[asyncpg.Record]; query: SELECT id, year, session, exercise_id, topic, subtopic, question_type, marks, content, 1 - (embedding <=> $1::vector) AS similarity FROM chunks WHERE source_type = 'past_exam' AND ($2::text IS NULL OR topic ILIKE $2) AND ($3::text IS NULL OR question_type = $3) AND ($4::int IS NULL OR year >= $4) AND ($5::int IS NULL OR year <= $5) ORDER BY embedding <=> $1::vector LIMIT $6; call await pgvector.asyncpg.register_vector(conn) at start of function; implement get_answer_key(conn: asyncpg.Connection, year: int, session: int, exercise_id: int) → str | None: SELECT content FROM chunks WHERE source_type = 'answer_key' AND year = $1 AND session = $2 AND exercise_id = $3 LIMIT 1

- [X] T034 [US3] Implement app/services/retrieval_service.py: implement retrieve_past_questions(query: str, topic: str | None, question_type: str | None, year_from: int | None, year_to: int | None, limit: int, secrets: AppSecrets, conn: asyncpg.Connection) → list[PastQuestion]; embed the query string via `await asyncio.to_thread(embed_text, query, secrets.voyage_api_key)` (the voyageai SDK is sync — wrap in a thread to avoid blocking the event loop; `embed_text` already maps Voyage failures to `EmbeddingServiceUnavailable`, so no extra try/except is needed here); call chunk_repo.cosine_similarity_search(conn, embedding, topic, question_type, year_from, year_to, limit); for each returned row call chunk_repo.get_answer_key(conn, row["year"], row["session"], row["exercise_id"]); build and return list[PastQuestion] domain models (chunk_id=UUID(row["id"]), year, session, topic, subtopic, question_type, marks, content, answer=answer_content)

- [X] T035 [US3] Create app/api/routers/questions.py: define QuestionRetrieveRequest(BaseModel) with fields query: str, topic: str | None = None, question_type: str | None = None, year_from: int | None = None, year_to: int | None = None, limit: int = Field(default=10, ge=1, le=50); router = APIRouter(prefix="/questions", tags=["questions"]); POST /retrieve endpoint: depends on current_active_user, get_secrets(), and get_db_conn() from app/api/dependencies.py (inject asyncpg.Connection via Depends — do NOT call asyncpg.connect() directly inside the handler); call retrieval_service.retrieve_past_questions(conn=conn, ...); return {"total_returned": len(results), "questions": [q.model_dump() for q in results]} or {"total_returned": 0, "questions": [], "suggestion": "No past questions found for this query. Try broadening the year range or topic."} when empty; NOTE: FR-011 natural-language intent extraction via Claude agent tool is deferred to Phase 4 — Phase 3 retrieval uses semantic embedding similarity only

### US4 — Topic Frequency Analytics

- [X] T036 [P] [US4] Implement app/repositories/topic_stats_repo.py: implement get_all_topic_stats(session: AsyncSession) → list[TopicStatsORM] using select(TopicStatsORM).order_by(TopicStatsORM.appearances.desc()); implement get_questions_by_topic(session: AsyncSession, topic: str, year_from: int | None = None, year_to: int | None = None, question_type: str | None = None, limit: int = 50) → list[ChunkORM]: first verify topic exists with select(TopicStatsORM).where(TopicStatsORM.topic == topic) — raise TopicNotFound if result is None; then query chunks with select(ChunkORM).where(ChunkORM.source_type == "past_exam", ChunkORM.topic == topic, ...).order_by(ChunkORM.year.desc()).limit(limit); apply year_from / year_to / question_type filters only when not None

- [X] T037 [US4] Implement app/services/topic_service.py: implement get_all_topic_stats(session: AsyncSession) → list[TopicStat]: call topic_stats_repo.get_all_topic_stats(); for each ORM row compute frequency_tier — high if appearances >= 14 (~7+ of last 10 years at 2 sessions/year), medium if 7–13, low if <= 6; return list[TopicStat] domain models; implement get_questions_by_topic(session: AsyncSession, conn: asyncpg.Connection, topic: str, year_from: int | None, year_to: int | None, question_type: str | None, limit: int) → list[PastQuestion]: call topic_stats_repo.get_questions_by_topic(); for each ChunkORM row call chunk_repo.get_answer_key(conn, orm.year, orm.session, orm.exercise_id) → answer; convert to PastQuestion(chunk_id=orm.id, year, session, topic, subtopic, question_type, marks, content, answer=answer); return list; NOTE: get_questions_by_topic requires both an AsyncSession (for SQLAlchemy repo queries) and an asyncpg.Connection (for chunk_repo answer key lookup) — both injected from api/dependencies.py in T038

- [X] T038 [US4] Create app/api/routers/topics.py: router = APIRouter(prefix="/topics", tags=["topics"]); GET /stats endpoint: depends on current_active_user, get_async_session(); call topic_service.get_all_topic_stats(session); return {"topics": [t.model_dump() for t in stats]}; GET /{topic}/questions endpoint: path param topic: str, optional query params year_from: int | None = None, year_to: int | None = None, question_type: str | None = None, limit: int = Query(default=50, le=200); depends on current_active_user, get_async_session(), and get_db_conn() (for answer key lookup); call topic_service.get_questions_by_topic(session=session, conn=conn, topic=topic, ...); return {"topic": topic, "total_returned": len(questions), "questions": [q.model_dump() for q in questions]}

### Integration & Checkpoint

- [X] T039 Wire Phase 3 routers into app/main.py: add imports `from app.api.routers import questions as _questions` and `from app.api.routers import topics as _topics`; add `app.include_router(_questions.router)` and `app.include_router(_topics.router)` after the existing health/auth router includes

- [X] T040 Verify Phase 3 checkpoint: with Docker stack running (db, redis, vault, api), GET /topics/stats with Bearer token → returns JSON array of topics with frequency_tier in < 3 s; POST /questions/retrieve with body {"query": "integration questions from 2015 to 2024"} → returns questions with content and answer fields in < 5 s; GET /topics/Functions/questions → returns question list filtered by topic; confirm /topics/stats hits no LLM (check logs for no anthropic/voyage calls)

---

## Plan Phase 4 — Exam Generation + Chat

**Purpose**: Stream mock exams via Claude (US1), topic explanation + guardrails (US5, US6, US7).
All Claude responses stream as SSE. Curriculum JSON injected into every system prompt.

**API surface**: `POST /exams/generate`, `GET /exams/active`, `GET /exams/{session_id}`, `POST /chat`

### Shared Infrastructure (parallel, no story label)

- [X] T041 [P] Create `app/infra/llm/__init__.py` (empty) and implement `app/infra/llm/claude.py`: `stream_claude(messages: list, system: str, api_key: str, tools: list | None = None) -> AsyncGenerator[str, None]` — use `anthropic.AsyncAnthropic(api_key=api_key).messages.stream(model="claude-sonnet-4-5", max_tokens=4096, system=system, messages=messages, tools=tools or [])` as async context manager; for each text chunk yield `f"data: {json.dumps({'event': 'token', 'text': text})}\n\n"`; after stream exits yield `"data: [DONE]\n\n"`; wrap anthropic.APIStatusError in AIServiceUnavailable; also implement `call_claude(messages: list, system: str, api_key: str, max_tokens: int = 2048) -> str` for non-streaming evaluator calls

- [X] T042 [P] Create `app/infra/llm/tools.py`: define three Anthropic tool-schema dicts — `RETRIEVE_PAST_QUESTIONS_TOOL` (name="retrieve_past_questions", description, input_schema with query: str, topic?: str, question_type?: str, year_from?: int, year_to?: int, limit?: int), `RETRIEVE_ANSWER_KEY_TOOL` (name="retrieve_answer_key", input_schema with year: int, session: int, exercise_id: int), `GET_TOPIC_STATS_TOOL` (name="get_topic_stats", input_schema with topic?: str); export as `ALL_TOOLS = [RETRIEVE_PAST_QUESTIONS_TOOL, RETRIEVE_ANSWER_KEY_TOOL, GET_TOPIC_STATS_TOOL]`

- [X] T043 [P] Create `app/data/__init__.py` (empty) and `app/data/curriculum.json`: `{"academic_year": "2024-2025", "in_scope": ["Functions", "Limits and Asymptotes", "Derivatives", "Integrals", "Complex Numbers", "Geometry in Space", "Probability", "Numerical Sequences", "Differential Equations", "Logarithmic and Exponential Functions"], "out_of_scope": ["Oblique Asymptotes", "Polar Coordinates", "Taylor Series", "Statistics beyond basic probability"]}` — this file is read once at module import in exam_service.py and chat_service.py via `pathlib.Path(__file__).parent.parent / "data" / "curriculum.json"`

- [X] T044 [P] Create `app/data/few_shot_exams/exam_2024_s1.json` and `app/data/few_shot_exams/exam_2023_s1.json`: each is a JSON object matching the ExamContent Pydantic model shape — `{"exercises": [{"id": 1, "topic": "...", "total_marks": 7, "content": "...", "parts": [{"part": "1", "marks": 2, "content": "..."}]}]}` — extract 3–4 exercises from the corresponding real exam PDF in `Math_GS_Exams_English/` (use pdfplumber or read existing chunk content from the DB); these are baked into the exam generation system prompt as few-shot structural examples

- [X] T045 [P] ~~Create `app/infra/embeddings/guardrails.py` (cosine-anchor approach)~~ **SUPERSEDED — replaced by a standalone NeMo Guardrails microservice.** The original in-process cosine-anchor embedding check proved too coarse; off-topic classification was moved to a dedicated `guardrails-service/` container. The old `app/infra/embeddings/guardrails.py` file was removed. Actual deliverable: create `guardrails-service/` (own Dockerfile + requirements.txt) — `main.py` is a FastAPI app exposing `POST /check` → `{"off_topic": bool}` and `GET /health`; it loads `nemoguardrails.LLMRails` from `config/` at startup and registers a custom system action `check_math_topic` that makes ONE `claude-haiku-4-5-20251001` call asking whether the message is about Lebanese GS Math (Yes/No); `config/config.yml` sets the NeMo main engine to anthropic claude-haiku; `config/rails.co` defines an input flow that runs `check_math_topic` and, when off-topic, returns the hardcoded `"OFF_TOPIC"` sentinel with no extra LLM call; the service reads `ANTHROPIC_API_KEY` from env (documented Vault-first exception); fails open (treats as on-topic) on any NeMo error. Add the `guardrails` service to `docker-compose.yml` (port 8100, healthcheck on /health) and inject `GUARDRAILS_URL=http://guardrails:8100` into the api service

- [X] T046 [P] Create `app/repositories/exam_repo.py`: `create_session(session: AsyncSession, user_id: UUID, session_type: SessionType, exam_content: dict, answer_key: dict, expires_at: datetime) -> ExamSessionORM`; `get_session(session: AsyncSession, session_id: UUID) -> ExamSessionORM | None`; `get_active_session(session: AsyncSession, user_id: UUID) -> ExamSessionORM | None` — WHERE user_id=user_id AND status='in_progress' AND expires_at > now(); `update_session_status(session: AsyncSession, session_id: UUID, status: SessionStatus) -> None`; `save_result(session: AsyncSession, session_id: UUID, user_id: UUID, student_answers: dict, evaluator_1: dict, evaluator_2: dict, total_score_1: float, total_score_2: float, discrepancy_flagged: bool) -> ExamResultORM`; `get_result(session: AsyncSession, session_id: UUID) -> ExamResultORM | None`; `get_history(session: AsyncSession, user_id: UUID, limit: int = 20, offset: int = 0) -> tuple[int, list[ExamResultORM]]` — returns (total_count, page)

- [X] T047 [P] Create `app/repositories/message_repo.py`: `create_conversation(session: AsyncSession, user_id: UUID) -> ConversationORM`; `get_conversation(session: AsyncSession, conversation_id: UUID) -> ConversationORM | None`; `add_message(session: AsyncSession, conversation_id: UUID, role: MessageRole, content: str, guardrails_score: float | None = None) -> MessageORM`; `get_messages(session: AsyncSession, conversation_id: UUID, limit: int = 20) -> list[MessageORM]` — ordered by created_at ASC, most recent `limit` rows

### US1 — Mock Exam Generation

- [X] T048 [US1] Implement `app/services/exam_service.py`: load `curriculum.json` and `app/data/few_shot_exams/*.json` at module level via pathlib; `_build_generation_system_prompt() -> str` — compose system prompt including full curriculum scope, few-shot exam JSON structures, and instruction to output a 20-point Lebanese GS Math exam; `generate_exam(user_id: UUID, secrets: AppSecrets, db_session: AsyncSession, redis: Redis) -> AsyncGenerator[str, None]`: call `exam_repo.get_active_session()` — if found raise `ActiveSessionExists(active_session_id=..., expires_at=...)`; create DB session via `exam_repo.create_session(status=in_progress, expires_at=now()+3h)`; yield `f"data: {json.dumps({'event': 'session_created', 'session_id': str(session.id), 'expires_at': session.expires_at.isoformat()})}\n\n"`; call `stream_claude(messages, system=build_generation_system_prompt(), api_key=secrets.anthropic_api_key)`; accumulate streamed text; parse final accumulated text to extract structured ExamContent and answer_key dicts; yield `f"data: {json.dumps({'event': 'exam_complete', 'exam_content': exam_content_dict})}\n\n"`; store answer_key in Redis via `set_session(redis, str(session.id), {'answer_key': answer_key_dict})`; yield `"data: [DONE]\n\n"`; `get_active_session(user_id, db_session) -> ExamSessionORM` — raises ExamNotFound if none; `get_session_by_id(session_id, user_id, db_session) -> ExamSessionORM` — raises ExamNotFound if not found or not owned by user; raises SessionExpired if expires_at < now()

- [X] T049 [US1] Create `app/api/routers/exams.py`: `router = APIRouter(prefix="/exams", tags=["exams"])`; `class GenerateRequest(BaseModel): session_type: SessionType = SessionType.mock_generated`; `POST /generate`: depends on current_active_user, get_async_session(), get_redis(), get_secrets(); returns `StreamingResponse(exam_service.generate_exam(...), media_type="text/event-stream")`; `GET /active`: depends on current_active_user, get_async_session(); returns session JSON (exam_content included, answer_key never exposed); `GET /{session_id}`: depends on current_active_user, get_async_session(); returns session JSON with created_at, expires_at, status, exam_content; answer_key never included in any response

### US5 + US6 + US7 — Chat, Curriculum Scope, Guardrails

- [X] T050 [US5] Implement `app/services/guardrails_service.py`: `async classify_message(text: str) -> bool` — returns True if off-topic; only classifies if `len(text.split()) >= 10` (short messages always return False — Decision 5); otherwise POSTs `{"message": text}` to `{GUARDRAILS_URL}/check` via `httpx.AsyncClient` (timeout 10s) and returns the `off_topic` field; maps `httpx.HTTPStatusError`/`httpx.RequestError` to `AIServiceUnavailable`. `GUARDRAILS_URL` read from env (default `http://guardrails:8100`). NOTE: no longer takes `api_key`/`anchor_embeddings` — classification is delegated to the guardrails microservice (see T045). `async get_counter(redis, conversation_id) -> int` — calls `redis_client.get_guardrails_counter()`; returns 0 if missing; `async increment_counter(redis, conversation_id) -> int`; `async reset_counter(redis, conversation_id) -> None` — sets counter to 0; `get_guardrail_tier(counter: int) -> str` — "normal" if <= 1, "warning" if == 2, "block" if >= 3

- [X] T051 [US5] Implement `app/services/chat_service.py`: load `curriculum.json` at module level; `_build_chat_system_prompt(counter: int) -> str` — compose system prompt with Lebanese exam context, full curriculum scope (reads module-level `_curriculum`), and optional redirect reminder if counter == 2; `async handle_turn(conversation_id: UUID | None, message: str, user_id: UUID, secrets: AppSecrets, db_session: AsyncSession, redis: Redis) -> AsyncGenerator[str, None]` (NOTE: no `anchor_embeddings` param — guardrails delegated to the microservice via `guardrails_service.classify_message(message)`): if conversation_id is None create new via `message_repo.create_conversation()` + commit, yield `conversation_id` event; else `get_conversation()` and verify ownership (raise `ExamNotFound` if missing/not owned); save user message + commit; `off_topic = await guardrails_service.classify_message(message)`; get counter; if off-topic increment else reset to 0; tier = get_guardrail_tier(counter); if tier == "block" yield `guardrail_block` event then `"data: [DONE]\n\n"` and return; fetch last 20 messages; call `stream_claude(claude_messages, system=_build_chat_system_prompt(counter), api_key=secrets.anthropic_api_key)`; forward token events and accumulate full_response; if tier == "warning" after stream ends yield `guardrail_warning` event; yield `done` event then `"data: [DONE]\n\n"`; save assistant response via message_repo + commit

- [X] T052 [US5] Create `app/api/routers/chat.py`: `router = APIRouter(prefix="/chat", tags=["chat"])`; `class ChatRequest(BaseModel): conversation_id: UUID | None = None; message: str`; `@router.post("")` handler (mounted at `/chat`): depends on current_active_user, get_async_session(), get_redis(), get_secrets(); returns `StreamingResponse(chat_service.handle_turn(conversation_id=..., message=..., user_id=user.id, secrets=..., db_session=..., redis=...), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})`. NOTE: no anchor-embedding precompute — off-topic classification is handled by the guardrails microservice inside `handle_turn`

### Integration & Checkpoint

- [X] T053 Wire Phase 4 routers into `app/main.py`: add `from app.api.routers import exams as _exams` and `from app.api.routers import chat as _chat`; add `app.include_router(_exams.router)` and `app.include_router(_chat.router)` after existing router includes

- [X] T054 Verify Phase 4 checkpoint: `POST /exams/generate` with Bearer token → SSE stream begins within 2s with session_created event, completes with exam_complete event; `GET /exams/active` → returns the in-progress session; `POST /chat` with message "explain integration by parts" → streams Lebanese-exam-grounded explanation; `POST /chat` with 3 consecutive off-topic messages → third response contains guardrail_block event with no AI content; check Docker logs confirm no out-of-scope topic appears in generated exam

---

## Plan Phase 5 — Dual Evaluator + Results

**Purpose**: Answer submission triggers two parallel AI graders; results stored permanently (US2).

**API surface**: `POST /exams/{session_id}/submit`, `GET /exams/{session_id}/results`, `GET /exams/history`

### US2 — Answer Submission and Dual Evaluation

- [X] T055 [US2] Implement `app/services/grading_service.py`: `_build_evaluator_prompt(persona: str, exam_content: dict, answers: list[dict], answer_key: dict) -> str` — compose per-evaluator system prompt; persona="strict" instructs deduct on doubt; persona="lenient" instructs award on doubt; prompt includes exam_content structure, student answers, and official answer key; `_call_evaluator(persona, exam_content, answers, answer_key, api_key) -> EvaluatorScore` — calls `call_claude()` (non-streaming); instructs model to return JSON with fields matching EvaluatorScore: `scores: dict[str, float]` keyed by "Q{ex}_{part}", `total: float`, `feedback: str`, `missing_keywords: list[str]`; parses JSON response; `_detect_discrepancy(ev1: EvaluatorScore, ev2: EvaluatorScore) -> tuple[bool, str | None]` — compare scores dicts; flagged=True if any key has different values; details string lists differing sub-questions; `submit_answers(session_id: UUID, user_id: UUID, answers: list[dict], db_session: AsyncSession, redis: Redis, secrets: AppSecrets) -> AsyncGenerator[str, None]`: fetch session via exam_repo; verify ownership; verify status is in_progress (raise InvalidAnswerSubmission if already submitted); verify not expired (raise SessionExpired); validate answer exercise_ids match exam_content exercise ids (raise InvalidAnswerSubmission); fetch answer_key dict from Redis via `get_session(redis, str(session_id))`; yield evaluating event; run `asyncio.gather(asyncio.to_thread(_call_evaluator, "strict", ..., secrets.anthropic_api_key), asyncio.to_thread(_call_evaluator, "lenient", ..., secrets.anthropic_api_key))`; yield evaluator_1_complete and evaluator_2_complete events; compute discrepancy; save via `exam_repo.save_result()`; update session status to "graded" via `exam_repo.update_session_status()`; yield grading_complete event with full EvaluationResult JSON; yield `"data: [DONE]\n\n"`; `get_results(session_id: UUID, user_id: UUID, db_session: AsyncSession) -> EvaluationResult` — fetches from exam_repo.get_result(); raises ExamNotFound if not available; verifies ownership. **Implementation notes (deviations from spec above):** (1) answer key is read from the authoritative DB column `row.answer_key` (loaded with the session for the ownership/status checks), NOT from Redis — the Redis copy has a 3h TTL and adds an expiry failure mode for no benefit; (2) `discrepancy_details` is not persisted (no column on `ExamResultORM`), so `get_results` recomputes it from the two stored evaluator score dicts via `_detect_discrepancy`; (3) `_detect_discrepancy` compares the UNION of both score dicts' keys so a key present in only one evaluator counts as a discrepancy; (4) `expires_at` is normalised to tz-aware before comparison; (5) evaluator JSON parsing strips ```` ``` ```` fences defensively; (6) **pre-flight validation is split into a separate `validate_submission(...)` coroutine that the router `await`s BEFORE constructing the `StreamingResponse`** — raising the validation exceptions inside the generator would fire them *after* Starlette has already sent HTTP 200 + headers, so they could never map to 404/410/422 (Principle IV). `submit_answers` now receives `(exam_content, answer_key)` and only streams; an evaluator JSON failure mid-stream is surfaced as an SSE `error` event (not a raise, which can no longer set a status). `redis` param dropped (answer key comes from the DB row). Verified end-to-end: `POST /exams/{random-uuid}/submit` with a valid token returns `404` + JSON `ErrorResponse` (not a 200 stream)

- [X] T056 [US2] Create `app/api/routers/grading.py`: `router = APIRouter(prefix="/exams", tags=["grading"])`; `class AnswerPart(BaseModel): part: str; answer: str; submitted_at: datetime`; `class ExerciseAnswer(BaseModel): exercise_id: int; parts: list[AnswerPart]`; `class SubmitRequest(BaseModel): answers: list[ExerciseAnswer]`; `POST /{session_id}/submit`: depends on current_active_user, get_async_session(), get_redis(), get_secrets(); converts `body.answers` to `list[dict]` via `model_dump(mode="json")`; returns `StreamingResponse(grading_service.submit_answers(...), media_type="text/event-stream")` with no-cache headers; `GET /{session_id}/results`: depends on current_active_user, get_async_session(); calls grading_service.get_results(); returns EvaluationResult JSON; `GET /history`: query params limit: int = Query(default=20, le=100), offset: int = Query(default=0, ge=0); depends on current_active_user, get_async_session(); calls exam_repo.get_history(); returns `{"total": N, "results": [...]}` (each result: session_id, total_score_1, total_score_2, discrepancy_flagged, created_at)

- [X] T057 Wire Phase 5 router into `app/main.py`: add `from app.api.routers import grading as _grading`; add `app.include_router(_grading.router)` **BEFORE** the exams router include (NOT after, as originally written). Both routers share the `/exams` prefix; Starlette matches in registration order, so the exams router's `GET /{session_id}` param route would otherwise capture `GET /exams/history` and 422 on UUID coercion. Registering grading first lets its literal `/history` resolve correctly while its 2-segment `/{session_id}/submit|results` routes never collide with exams' routes. Verified by route-resolution test: `/exams/history`→get_history, `/exams/active`→get_active_session, `/exams/{uuid}`→get_session, `/exams/{uuid}/results`→get_results, `/exams/{uuid}/submit`→submit_answers

- [ ] T058 Verify Phase 5 checkpoint: `POST /exams/{id}/submit` → SSE streams evaluating → evaluator_1_complete → evaluator_2_complete → grading_complete within 60s; `GET /exams/{id}/results` → returns full dual evaluation JSON with discrepancy_flagged; `GET /exams/history` → returns paginated list of past results; verify `exam_results` table has a permanent row for the submission. **STATIC VERIFICATION DONE** (`py_compile` clean; `app.main` imports successfully; route-resolution test confirms all 5 `/exams` routes resolve to the correct handlers with no `/history` shadowing; TestClient test confirms `POST /exams/{uuid}/submit` on a missing session returns a mapped 404 JSON error, not a 200 stream). **LIVE RUN PENDING** — full SSE-timing + dual-evaluator + DB-row verification requires the Docker stack up with a real `ANTHROPIC_API_KEY`; run `docker compose up -d` then exercise the endpoints with a Bearer token.

---

## Plan Phase 6 — React Frontend

**Purpose**: Students can use the full platform in a browser (all user stories).

**Stack**: React 18 + Vite + TypeScript + Tailwind CSS 3 + KaTeX + React Router DOM

### Shared Frontend Services & Hooks

- [ ] T059 [P] Create `frontend/src/services/api.ts`: export `API_BASE = ""`; typed fetch helpers — `login(email: string, password: string): Promise<{access_token: string}>` (FormData POST to /auth/jwt/login); `register(email, password): Promise<User>`; `getTopicStats(token): Promise<TopicsResponse>`; `getTopicQuestions(topic, token, opts?): Promise<TopicQuestionsResponse>`; `retrieveQuestions(body, token): Promise<QuestionsResponse>`; `getActiveSession(token): Promise<Session>`; `getSessionById(id, token): Promise<Session>`; `getResults(sessionId, token): Promise<EvaluationResult>`; `getHistory(token, opts?): Promise<HistoryResponse>`; all return typed interfaces defined in `frontend/src/types.ts`; all include `Authorization: Bearer {token}` header; non-2xx responses throw typed APIError

- [ ] T060 [P] Create `frontend/src/services/sse.ts`: `streamSSE(url: string, body: object, token: string, onEvent: (event: string, payload: any) => void): {abort: () => void}` — uses `fetch()` with POST + auth header; reads `response.body` as `ReadableStream<Uint8Array>`; decodes with TextDecoder; splits on `\n\n`; each `data: {...}` line parsed as JSON; calls `onEvent(parsed.event, parsed)`; stops on `[DONE]`; returns `{abort: () => void}` wrapping AbortController

- [ ] T061 [P] Create `frontend/src/hooks/useSSEStream.ts`: `useSSEStream() -> {stream, isStreaming, error, start(url, body, token, onEvent), abort}` — wraps sse.ts with React state; `frontend/src/hooks/useExamSession.ts`: `useExamSession(token) -> {session, isGenerating, generate(), isSubmitting, submit(answers)}` — orchestrates SSE calls for exam generation and submission; `frontend/src/hooks/useTopicStats.ts`: `useTopicStats(token) -> {topics, isLoading, error, refetch}` — fetches /topics/stats on mount

- [ ] T062 [P] Create `frontend/src/pages/LoginPage.tsx` — email + password form, calls `api.login()`, stores token in `localStorage.setItem('token', ...)`, redirects to `/exam`; `frontend/src/pages/RegisterPage.tsx` — email + password form, calls `api.register()`, on success redirects to `/login`; both pages styled with Tailwind

### US1 — Exam Generation UI

- [ ] T063 [P] [US1] Create exam components and page: `frontend/src/components/exam/ExamRenderer.tsx` — renders ExamContent exercises using KaTeX (`import katex from 'katex'`) for math in backtick-delimited segments; `frontend/src/components/exam/AnswerInput.tsx` — textarea per exercise part with label showing marks; `frontend/src/components/exam/SessionTimer.tsx` — countdown timer from `expires_at` ISO string, shows MM:SS, red when < 5 min; `frontend/src/pages/ExamPage.tsx` — "Generate Exam" button calls useSSEStream for POST /exams/generate; shows streaming text during generation; on exam_complete event renders ExamRenderer + AnswerInput per part; submit button calls useSSEStream for POST /exams/{id}/submit and redirects to /results/{id} on grading_complete

### US2 — Results UI

- [ ] T064 [P] [US2] Create results components and pages: `frontend/src/components/results/DualScoreCard.tsx` — side-by-side table of evaluator_1 vs evaluator_2 scores per sub-question; `frontend/src/components/results/DiscrepancyBadge.tsx` — orange "!" badge shown on sub-questions where evaluator scores differ; `frontend/src/components/results/FeedbackPanel.tsx` — shows feedback text + missing_keywords list for one evaluator; `frontend/src/pages/ResultsPage.tsx` — fetches GET /exams/:sessionId/results; renders DualScoreCard with DiscrepancyBadges; shows both FeedbackPanels side by side; shows discrepancy_details if flagged; `frontend/src/pages/HistoryPage.tsx` — fetches GET /exams/history; lists past results as cards with date, scores, link to ResultsPage

### US3 — Past Questions UI

- [ ] T065 [P] [US3] Create `frontend/src/pages/QuestionsPage.tsx`: search form with fields query (text), topic (select from known topics list), year_from/year_to (number inputs), question_type (select: proof/calculation/mcq/sketch), limit (default 10); on submit calls POST /questions/retrieve via api.ts; renders result list — each card shows year, session, topic, subtopic, marks, content (with KaTeX rendering), answer (collapsible); shows "no results" message with suggestion text when empty

### US4 — Topic Analytics UI

- [ ] T066 [P] [US4] Create topic analytics components and page: `frontend/src/components/topics/FrequencyBadge.tsx` — red chip for "high", amber for "medium", green for "low"; `frontend/src/components/topics/TopicTable.tsx` — table rows: topic name, appearances count, last_seen_year, FrequencyBadge; clicking row navigates to /topics/{topic}; `frontend/src/components/topics/TopicQuestionList.tsx` — list of PastQuestion cards with year/session/content/answer; `frontend/src/pages/TopicsPage.tsx` — uses useTopicStats hook; renders TopicTable; on row click fetches GET /topics/{topic}/questions with optional year_from/year_to filter inputs and renders TopicQuestionList below

### US5 — Chat UI

- [ ] T067 [P] [US5] Create chat components and page: `frontend/src/components/chat/StreamingMessage.tsx` — renders accumulating text tokens with KaTeX for math; `frontend/src/components/chat/GuardrailBanner.tsx` — yellow warning banner for guardrail_warning event, red block banner for guardrail_block event; `frontend/src/components/chat/ChatThread.tsx` — scrollable message list with user bubbles (right-aligned, blue) and assistant bubbles (left-aligned, grey) using StreamingMessage; `frontend/src/pages/ChatPage.tsx` — text input + send button; stores conversation_id in state; on send calls useSSEStream for POST /chat; handles SSE events: token (accumulate to current assistant message), guardrail_warning (show GuardrailBanner below current message), guardrail_block (replace message with red GuardrailBanner), done (finalize current message), conversation_id (store)

### Integration & Checkpoint

- [ ] T068 Install React Router: `cd frontend && npm install react-router-dom`; create `frontend/src/App.tsx` with `<BrowserRouter>` + `<Routes>`: `/login` → LoginPage, `/register` → RegisterPage, `/exam` → ExamPage (ProtectedRoute), `/results/:sessionId` → ResultsPage (ProtectedRoute), `/history` → HistoryPage (ProtectedRoute), `/topics` → TopicsPage (ProtectedRoute), `/questions` → QuestionsPage (ProtectedRoute), `/chat` → ChatPage (ProtectedRoute); implement `ProtectedRoute` wrapper that reads localStorage token and redirects to /login if absent; add nav header with links to Exam/Topics/Questions/Chat/History; update `frontend/src/main.tsx` to render `<App />`

- [ ] T069 Verify Phase 6 checkpoint: `cd frontend && npm run dev` starts on port 5173 with no errors; register and login work in browser; clicking Generate Exam streams text progressively; submitting answers produces dual score results page with discrepancy badges; TopicsPage shows color-coded frequency table; clicking a topic shows its questions; QuestionsPage search returns results with KaTeX math; ChatPage streams responses with guardrail banners on off-topic messages

---

## Plan Phase 7 — Polish

**Purpose**: Error states, final end-to-end validation of all SC-00x success criteria.

- [ ] T070 Implement error state UI in `frontend/src/components/ErrorBanner.tsx`: 503 service unavailable banner with "Retry" button that re-calls the failed operation; 409 active session conflict with "Resume Session" button linking to /exam with existing session loaded; 410 session expired message with "Start New Exam" button; integrate into ExamPage (handles 503 on generate + 409 active session), ResultsPage (handles 404 no results yet), ChatPage (handles 503 on chat); all API error cases must display a human-readable message, never a raw HTTP error

- [ ] T071 Final end-to-end smoke test and checkpoint: verify all 9 success criteria — SC-001: exam generates first token < 5s, completes < 30s; SC-002: dual evaluation both results displayed < 60s; SC-003: topics dashboard loads < 3s with no LLM call in logs; SC-004: past question retrieval < 5s for any topic/year query; SC-005: asking about out-of-scope topic (e.g. "explain oblique asymptotes") returns explicit out-of-scope notice; SC-006: discrepancy badges visible on results page without manual score comparison; SC-007: third consecutive off-topic message triggers guardrail_block in same response turn; SC-008: active exam session remains accessible after 2h without re-auth; SC-009: editing `app/data/curriculum.json` and restarting API causes new exam to respect updated scope immediately

---

## Dependencies & Execution Order

### Phase Dependencies

- **Plan Phase 1 — Infrastructure Foundation (T001–T025)**: Complete ✅
- **Plan Phase 2 — Ingestion Pipeline (T026–T031)**: Complete ✅
- **Plan Phase 3 — RAG Retrieval + Topic Analytics (T032–T040)**: Complete ✅
- **Plan Phase 4 — Exam Generation + Chat (T041–T054)**:
  - T041–T047 — no dependencies, start immediately [P]
  - T048 [US1] — depends on T041, T042, T043, T044, T046
  - T050 [US5] — depends on T045
  - T049 [US1] — depends on T048
  - T051 [US5] — depends on T041, T043, T047, T050
  - T052 [US5] — depends on T051
  - T053 — depends on T049 + T052
  - T054 — checkpoint after T053
- **Plan Phase 5 — Dual Evaluator + Results (T055–T058)**: Code complete ✅ (T055–T057); checkpoint T058 statically verified, live run pending
  - T055 [US2] — depends on T041 (claude.py), T046 (exam_repo)
  - T056 [US2] — depends on T055
  - T057 — depends on T056 (register grading BEFORE exams — see T057 note)
  - T058 — checkpoint after T057
- **Plan Phase 6 — React Frontend (T059–T069)**:
  - T059–T062 — no dependencies, start immediately [P]
  - T063–T067 — depend only on T059 (api.ts) + T060 (sse.ts) + T061 (hooks) [P]
  - T068 — depends on T063–T067
  - T069 — checkpoint after T068 + full backend running
- **Plan Phase 7 — Polish (T070–T071)**:
  - T070 — depends on T068
  - T071 — depends on all Phase 4–6 complete

### Parallel Opportunities Within Phase 4

```
# Launch together (all independent):
T041 — app/infra/llm/claude.py
T042 — app/infra/llm/tools.py
T043 — app/data/curriculum.json
T044 — app/data/few_shot_exams/
T045 — guardrails-service/ (NeMo microservice; replaces the removed infra/embeddings/guardrails.py)
T046 — app/repositories/exam_repo.py
T047 — app/repositories/message_repo.py

# After T041+T042+T043+T044+T046:
T048 — app/services/exam_service.py

# After T045:
T050 — app/services/guardrails_service.py

# After T048:                   After T041+T043+T047+T050:
T049 — exams router             T051 — app/services/chat_service.py → T052 chat router

# After T049 + T052:
T053 — app/main.py wiring → T054 checkpoint
```

### Parallel Opportunities Within Phase 6

```
# All independent — launch together:
T059 — frontend/src/services/api.ts
T060 — frontend/src/services/sse.ts
T061 — frontend/src/hooks/
T062 — auth pages

# After T059+T060+T061:
T063 (US1 exam page) | T064 (US2 results) | T065 (US3 questions)
T066 (US4 topics)    | T067 (US5 chat)

# After T063–T067:
T068 — App.tsx routing → T069 checkpoint
```

---

## Notes

- [P] tasks operate on different files with no shared dependencies — safe to implement in parallel
- Ingestion pipeline reads credentials from CLI flags with env var fallbacks — it does NOT call Vault (offline script)
- `Math_GS_Exams_English/` contains 19 PDFs: years 2004–2024, Sessions 1 & 2, some Exceptional sessions
- Filename pattern: `Math_GS_English_{YEAR}_Session{N}.pdf` and `Math_GS_English_{YEAR}_Exceptional.pdf`
- voyage-large-2 produces 1536-d embeddings — matches ChunkORM Vector(1536) column
- claude-haiku model ID: `claude-haiku-4-5-20251001`; claude-sonnet model ID: `claude-sonnet-4-5`
- Embed batch size of 16 is safe for voyage-large-2 rate limits
- topic_stats is derived entirely from chunk metadata — no separate AI call needed
- chunk_repo.py uses asyncpg directly (not SQLAlchemy) because the pgvector `<=>` operator requires raw SQL; topic_stats_repo.py uses SQLAlchemy AsyncSession as normal
- Guardrails: off-topic classification runs in the standalone `guardrails-service` container (NeMo Guardrails + Claude Haiku), reached over HTTP via `GUARDRAILS_URL`. The original in-process cosine-anchor embedding approach (`app/infra/embeddings/guardrails.py`) was superseded and the module removed. `classify_message` short-circuits messages with < 10 words as on-topic before calling the service
- `call_claude()` (non-streaming) must be wrapped in `asyncio.to_thread()` when called from async context because the anthropic SDK's sync client blocks the event loop
- Answer key is stored in Redis (not returned to client) during active session; grading_service fetches it from Redis at submit time
- Frontend KaTeX rendering: wrap math expressions in `$...$` for inline or `$$...$$` for block; use `katex.renderToString()` in component render
