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
- [X] T008 Create docker-compose.yml with all 7 services — full spec below:
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

## Dependencies & Execution Order

### Phase Dependencies

- **Plan Phase 1 — Infrastructure Foundation (T001–T025)**: Complete ✅
- **Plan Phase 2 — Ingestion Pipeline (T026–T031)**:
  - T026 (pdf_extractor) — no dependencies, start immediately
  - T027 (chunker) — no dependencies, start immediately
  - T028 (tagger) — no dependencies, start immediately
  - T029 (embedder) — no dependencies, start immediately
  - T030 (pipeline) — depends on T026, T027, T028, T029 all complete
  - T031 (checkpoint) — depends on T030 complete + Docker stack running

### Parallel Opportunities Within Phase 3

```
# Launch together (no interdependencies):
T026 — ingestion/pdf_extractor.py
T027 — ingestion/chunker.py
T028 — ingestion/tagger.py
T029 — ingestion/embedder.py  (wait for T026-T028 results first if sequential)

# Then in sequence:
T030 — ingestion/pipeline.py  — after T026, T027, T028, T029
T031 — checkpoint              — after T030 + docker compose up
```

---

## Notes

- [P] tasks operate on different files with no shared dependencies — safe to implement in parallel
- Ingestion pipeline reads credentials from CLI flags with env var fallbacks — it does NOT call Vault (offline script)
- `Math_GS_Exams_English/` contains 20 PDFs: years 2004–2024, Sessions 1 & 2, some Exceptional sessions
- Filename pattern: `Math_GS_English_{YEAR}_Session{N}.pdf` and `Math_GS_English_{YEAR}_Exceptional.pdf`
- voyage-large-2 produces 1536-d embeddings — matches ChunkORM Vector(1536) column
- claude-haiku model ID: `claude-haiku-4-5-20251001`
- Embed batch size of 16 is safe for voyage-large-2 rate limits
- topic_stats is derived entirely from chunk metadata — no separate AI call needed
- Phase 4+ tasks (RAG, Exam Generation, Dual Evaluator, Frontend, Polish) to be added via subsequent `/speckit-tasks` runs
