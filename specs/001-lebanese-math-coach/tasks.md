---
description: "Task list for Lebanese Math Coach — Phase 1: Infrastructure Foundation only"
---

# Tasks: Lebanese Math Coach — Phase 1

**Input**: Design documents from `specs/001-lebanese-math-coach/`

**Prerequisites**: plan.md ✅ | spec.md ✅ | research.md ✅ | data-model.md ✅ | contracts/ ✅

**Scope note**: This file covers **Plan Phase 1 — Infrastructure Foundation (Days 1–2)** only.
Phases 2–7 (Ingestion, RAG, Exam Generation, Dual Evaluator, Frontend, Polish) will be added
in subsequent `/speckit-tasks` runs.

**Tests**: Not requested — no test tasks generated.

---

## Phase 1: Setup (Project Scaffolding)

**Purpose**: Create the repository skeleton, Docker config, and dependency manifests so every
developer and CI environment starts from the same structure.

- [ ] T001 Create the full app/ directory structure per plan.md: app/api/routers/, app/api/, app/services/, app/repositories/, app/domain/, app/infra/llm/, app/infra/embeddings/, app/data/few_shot_exams/ (empty __init__.py in each Python package)
- [ ] T002 [P] Create ingestion/ directory structure with empty __init__.py files: ingestion/pipeline.py, ingestion/pdf_extractor.py, ingestion/chunker.py, ingestion/tagger.py, ingestion/embedder.py (stub files with module docstrings only — implementation in Plan Phase 2)
- [ ] T003 [P] Create pyproject.toml at repo root with all backend dependencies: fastapi==0.115.*, sqlalchemy[asyncio]==2.0.*, fastapi-users[sqlalchemy]==13.*, anthropic, voyageai, redis[hiredis]>=5, minio, hvac, pdfplumber, pgvector, alembic, asyncpg, uvicorn[standard], pydantic>=2, pytest, pytest-asyncio
- [ ] T004 [P] Create frontend/ scaffold: run `npm create vite@latest frontend -- --template react-ts`, then install dependencies: katex, @types/katex, tailwindcss, postcss, autoprefixer; init Tailwind config
- [ ] T005 [P] Create frontend/vite.config.ts with dev proxy — proxy all requests `/*` to http://localhost:8000 (backend routes have no /api/ prefix per contracts; do NOT restrict proxy to /api/* only)
- [ ] T006 [P] Create .env.example at repo root with exactly two entries: VAULT_ADDR=http://vault:8200 and VAULT_TOKEN=dev-root-token; add .env to .gitignore
- [ ] T007 Create Dockerfile for api service: FROM python:3.12-slim, COPY pyproject.toml, RUN pip install ., COPY app/ app/, CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
- [ ] T008 Create docker-compose.yml with all 6 services — full spec below:
  - **db**: image postgres:16, env POSTGRES_DB=lebanese_math, healthcheck: pg_isready -U postgres
  - **redis**: image redis:7-alpine, healthcheck: redis-cli ping
  - **minio**: image minio/minio, command server /data --console-address :9001, healthcheck: curl -f http://localhost:9000/minio/health/live
  - **vault**: image hashicorp/vault, env VAULT_DEV_ROOT_TOKEN_ID=${VAULT_TOKEN}, VAULT_DEV_LISTEN_ADDRESS=0.0.0.0:8200, healthcheck: vault status
  - **migrate**: build from Dockerfile, command: alembic upgrade head, depends_on db (healthy) + vault (healthy), restart: on-failure
  - **api**: build from Dockerfile, ports 8000:8000, depends_on db (healthy) + redis (healthy) + vault (healthy) + migrate (service_completed_successfully), env_file .env

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Domain layer, infrastructure adapters, ORM models, Alembic migration, FastAPI app
wiring, auth, and health endpoint. MUST be complete before any user story phase begins.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

### Domain Layer

- [ ] T009 [P] Create app/domain/enums.py with four enums: SessionType (mock_generated | real_past_exam), SessionStatus (in_progress | submitted | graded), QuestionType (proof | calculation | mcq | sketch), MessageRole (user | assistant) — all inherit from (str, Enum)
- [ ] T010 [P] Create app/domain/exceptions.py with full hierarchy: base LebaneseCoachError(Exception); then ExamNotFound, AnswerKeyNotFound, TopicNotFound (→ HTTP 404); ActiveSessionExists (→ HTTP 409, include active_session_id and expires_at fields); SessionExpired (→ HTTP 410); InvalidAnswerSubmission (→ HTTP 422); AIServiceUnavailable, EmbeddingServiceUnavailable, VaultUnavailable (→ HTTP 503)
- [ ] T011 Create app/domain/models.py with all Pydantic domain models per data-model.md: ExercisePart, GraphSpec, Exercise, ExamContent, ExamSession, EvaluatorScore, EvaluationResult, PastQuestion, TopicStat, ErrorResponse (fields: error: str, request_id: str); no SQLAlchemy imports permitted in this file

### Infrastructure Adapters

- [ ] T012 Create app/infra/vault.py: define AppSecrets(BaseModel) with all secret fields (anthropic_api_key, voyage_api_key, db_password, db_url, minio_access_key, minio_secret_key, jwt_secret); implement resolve_secrets() — creates hvac.Client(url=VAULT_ADDR, token=VAULT_TOKEN), calls client.is_authenticated(), raises VaultUnavailable if false, reads kv secret at path "lebanese-math-coach", returns AppSecrets(**data)
- [ ] T013 [P] Create app/infra/redis_client.py: define SESSION_TTL = 10_800 and GUARDRAILS_TTL = 10_800 as module-level constants with inline comments justifying the TTL; implement async helpers: set_session(redis, session_id, data: dict), get_session(redis, session_id) → dict | None, delete_session(redis, session_id), get_guardrails_counter(redis, session_id) → int, set_guardrails_counter(redis, session_id, value: int), increment_guardrails_counter(redis, session_id) → int; every redis.set() MUST pass ex=SESSION_TTL or ex=GUARDRAILS_TTL
- [ ] T014 [P] Create app/infra/minio_client.py: implement get_minio_client(secrets: AppSecrets) → Minio; upload_pdf(client, bucket, filename, data: bytes); get_pdf_bytes(client, bucket, filename) → bytes; bucket name constant PAST_EXAMS_BUCKET = "past-exams"

### ORM Models

- [ ] T015 Create app/repositories/orm.py with all 7 ORM models per data-model.md using SQLAlchemy 2.0 mapped_column style: UserORM extending fastapi-users BaseUser[uuid.UUID] (single source of truth for the User entity — do NOT define a separate User model elsewhere), ConversationORM, MessageORM, ExamSessionORM (status and session_type use SQLAlchemy Enum mapped to domain enums; exam_content and answer_key use JSONB), ExamResultORM (no expires_at — permanent per FR-025), ChunkORM (include exercise_id: Mapped[int] column — required for answer key pairing per research.md Decision 7), TopicStatsORM; all import from app/domain/enums.py for enum types; no Pydantic imports

### Alembic Migration

- [ ] T016 Create alembic/env.py: configure async SQLAlchemy engine using DATABASE_URL constructed from Vault secrets at migration time (read from environment variable DATABASE_URL set by docker-compose migrate service); import all ORM models so autogenerate detects them; use run_async_migrations() pattern for asyncpg
- [ ] T017 Create alembic/versions/0001_baseline.py: CREATE EXTENSION IF NOT EXISTS vector; CREATE TABLE for all 7 tables matching ORM definitions in T015; CREATE INDEX chunks_embedding_hnsw_idx ON chunks USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64); this migration must be reversible (downgrade drops all tables and extension)

### FastAPI App Wiring

- [ ] T018 Create app/main.py: define @asynccontextmanager lifespan — calls resolve_secrets() (raises VaultUnavailable on failure → process exits), stores result in app.state.secrets, initialises redis pool in app.state.redis; add RequestIDMiddleware that generates uuid4() per request, attaches to request.state.request_id, and sets X-Request-ID response header; create FastAPI(lifespan=lifespan) app instance
- [ ] T019 Create app/api/exceptions.py: register @app.exception_handler for every exception in domain/exceptions.py; each handler must return JSONResponse(status_code=<correct code>, content=ErrorResponse(error=str(exc), request_id=request.state.request_id).model_dump()); catch-all handler for Exception returns 500 with same shape; MUST NOT leak stack traces
- [ ] T020 [P] Create app/api/dependencies.py: get_async_session() → AsyncSession (SQLAlchemy async sessionmaker using db_url from app.state.secrets); get_redis() → Redis (from app.state.redis); get_secrets() → AppSecrets (from app.state.secrets); current_active_user dependency via fastapi-users

### Authentication

- [ ] T021 Create auth configuration in app/infra/auth.py: import UserORM from app/repositories/orm.py (do NOT define a new SQLAlchemy model here — UserORM in repositories/orm.py is the single User model); define UserCreate, UserUpdate, UserRead Pydantic schemas; implement UserManager subclass with required password validation; configure JWTStrategy(secret=app.state.secrets.jwt_secret, lifetime_seconds=86400); configure BearerTransport(tokenUrl="/auth/jwt/login"); wire FastAPIUsers(user_model=UserORM, ...) instance
- [ ] T022 Create app/api/routers/auth.py: include fastapi-users auth_router (POST /auth/jwt/login, POST /auth/jwt/logout) and register_router (POST /auth/register); include users_router (GET /auth/me); register all three routers in app/main.py with prefix="" (fastapi-users handles prefixes internally)

### Health Endpoint

- [ ] T023 Create app/api/routers/health.py: implement GET /health — async handler that checks (1) vault: re-authenticates hvac client, (2) db: executes SELECT 1 via get_async_session(), (3) redis: sends PING via get_redis(); returns {"status": "ok", "vault": "connected", "db": "connected", "redis": "connected"} if all pass; returns 503 with failed services listed if any check fails; register router in app/main.py

### Phase 1 Checkpoint

- [ ] T024 Verify Phase 1 checkpoint: run `docker-compose up -d` → confirm all 6 services healthy via `docker-compose ps`; run `docker-compose run --rm migrate` → exits 0; run `curl http://localhost:8000/health` → returns {"status": "ok", ...}; run `curl -X POST http://localhost:8000/auth/register -d '{"email":"test@test.com","password":"pass123"}'` → returns 201; run `curl -X POST http://localhost:8000/auth/jwt/login -F "username=test@test.com" -F "password=pass123"` → returns access_token

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup completion
  - T009–T011 (domain layer): can start as soon as T001 creates directory structure
  - T012–T014 (infra adapters): depends on T011 (imports AppSecrets, domain models)
  - T015 (ORM models): depends on T009 (imports enums)
  - T016–T017 (Alembic): depends on T015 (imports ORM models)
  - T018 (main.py): depends on T012 (vault), T013 (redis)
  - T019 (exception handlers): depends on T010 (exceptions), T018 (app instance)
  - T020 (dependencies): depends on T018 (app.state)
  - T021 (auth config): depends on T015 (User ORM model), T018 (app.state.secrets)
  - T022 (auth routers): depends on T021
  - T023 (health router): depends on T020 (dependencies), T019 (exception shape)
  - T024 (checkpoint): depends on all of T001–T023

### Parallel Opportunities Within Phase 2

```
# Launch together (no interdependencies):
T009 — domain/enums.py
T010 — domain/exceptions.py
T013 — infra/redis_client.py
T014 — infra/minio_client.py
T020 — api/dependencies.py (after T018)

# Then in sequence:
T011 (domain/models.py) — after T009
T012 (infra/vault.py)   — after T011
T015 (orm.py)           — after T009
T016 (alembic/env.py)   — after T015
T017 (0001_baseline.py) — after T016
T018 (main.py)          — after T012, T013
T019 (exceptions.py)    — after T010, T018
T021 (auth config)      — after T015, T018
T022 (auth routers)     — after T021
T023 (health router)    — after T019, T020
T024 (checkpoint)       — after all above
```

---

## Notes

- [P] tasks operate on different files with no shared dependencies — safe to implement in parallel
- Every `redis.set()` call in infra/redis_client.py MUST pass `ex=SESSION_TTL` or `ex=GUARDRAILS_TTL` (Constitution Principle III)
- `infra/vault.py` MUST raise VaultUnavailable before the app serves any request (Constitution Principle II)
- `api/exceptions.py` MUST never return a stack trace (Constitution Principle IV)
- ORM models (repositories/orm.py) MUST NOT be imported by services/, api/, or domain/ (Constitution Principle I)
- Phases 2–7 tasks (Ingestion, RAG, Exam Generation, Dual Evaluator, Frontend, Polish) to be added via subsequent `/speckit-tasks` runs
