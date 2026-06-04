<!--
SYNC IMPACT REPORT
==================
Version change: (unversioned template) → 1.0.0
Bump type: MAJOR — initial constitution adoption; all principles newly defined from template placeholders.

Modified principles:
- All five principles newly authored (no prior definitions existed).

Added sections:
- I. Layered Architecture (NON-NEGOTIABLE)
- II. Infrastructure Contracts (NON-NEGOTIABLE)
- III. Streaming Runtime
- IV. Error Boundaries
- V. Security (NON-NEGOTIABLE)
- Tech Stack & Service Boundaries
- Development Workflow
- Governance

Removed sections:
- None (first adoption — template placeholders replaced throughout).

Templates requiring updates:
- .specify/templates/plan-template.md ✅ no changes required
  (Constitution Check section is already dynamically evaluated against the constitution file)
- .specify/templates/spec-template.md ✅ no changes required
- .specify/templates/tasks-template.md ✅ no changes required

Deferred TODOs:
- None. All fields fully resolved.
-->

# Lebanese Exam Coach Constitution

## Core Principles

### I. Layered Architecture (NON-NEGOTIABLE)

The backend MUST follow a strict five-layer structure: `api/` → `services/` → `repositories/` →
`domain/` and `infra/`. Routers in `api/` MUST NOT import SQLAlchemy models, Redis clients, or any
external service adapter directly. Business logic MUST live in `services/`; SQL MUST live in
`repositories/`; Pydantic domain models in `domain/` MUST remain distinct from ORM models and MUST
NOT be imported by `repositories/` or `infra/`. Each layer MUST only depend on the layer directly
below it — no skipping layers.

**Rationale**: Enforces a testable, replaceable dependency graph. Any layer violation leaks
infrastructure concerns into business logic, making services untestable without a running database
or live LLM connection.

### II. Infrastructure Contracts (NON-NEGOTIABLE)

All secrets (Anthropic API key, Voyage AI key, DB credentials, MinIO credentials) MUST be resolved
from HashiCorp Vault at application startup. The app MUST refuse to boot if Vault is unreachable —
no fallback to environment variables or hardcoded defaults is permitted.
The Alembic migration container MUST complete and exit with code 0 before the API container starts.
Docker Compose `depends_on` with `condition: service_completed_successfully` MUST enforce this
startup order.

**Rationale**: A running app with stale secrets or an un-migrated schema creates silent data
corruption and security exposure. Fail-fast at boot is safer than degraded runtime behaviour.

### III. Streaming Runtime

All LLM responses (exam generation, dual evaluation, topic explanation) MUST be streamed to the
React frontend via Server-Sent Events (SSE). No LLM response MUST be buffered and returned as a
single JSON payload.
Every Redis key MUST carry an explicit TTL set at write time with a documented justification in the
code comment at the call site. Keys MUST NOT be written without a TTL.

**Rationale**: Streaming reduces perceived latency for math exam generation (5–15 s responses).
Explicit Redis TTLs prevent unbounded memory growth and orphaned session keys.

### IV. Error Boundaries

Users MUST never see Python stack traces, SQLAlchemy errors, or raw exception messages. All
unhandled exceptions MUST be caught at the API boundary, logged internally with a `request_id`,
and returned to the client as structured JSON: `{"error": "<human message>", "request_id": "<uuid>"}`.
The domain exception hierarchy (e.g., `ExamNotFound`, `VaultUnavailable`, `OffTopicBlocked`) MUST
be defined in `domain/exceptions.py` and mapped to HTTP status codes exclusively inside `api/`
exception handlers. Services and repositories MUST raise domain exceptions only — never
`HTTPException`.

**Rationale**: Leaking stack traces exposes internal architecture and is a security risk. Mapping
exceptions only at the API boundary keeps lower layers ignorant of HTTP semantics, preserving
isolated unit testability.

### V. Security (NON-NEGOTIABLE)

No secret value MUST appear in source code, Git history, Docker images, or environment variables,
except the Vault root/dev token which is permitted solely in the local `.env` file and MUST be
listed in `.gitignore`. All user-supplied input (request bodies, query parameters, path parameters)
MUST be validated via Pydantic models at the API boundary before reaching any service layer. Raw
`dict` or unvalidated data from requests MUST NOT be passed to services.

**Rationale**: Lebanese student data and Anthropic API credentials are the highest-value assets.
A single committed secret invalidates the entire security posture. Input validation at the boundary
prevents injection and type-confusion attacks propagating into the domain.

## Tech Stack & Service Boundaries

| Layer | Technology | Notes |
|---|---|---|
| Backend | FastAPI (Python 3.12) | Routers, dependency injection, SSE responses |
| ORM | SQLAlchemy 2.0 (async) | Models strictly contained within `repositories/` |
| Vector DB | PostgreSQL 16 + pgvector | 1536-dimension embeddings + structured metadata |
| Object storage | MinIO | Raw PDF storage for past exams |
| Session memory | Redis 7 | Active sessions (TTL 3 h), answer keys, guardrails counters |
| Secrets | HashiCorp Vault (dev mode) | All credentials resolved at boot |
| LLM — primary | claude-sonnet-4-5 | Exam generation, dual evaluation, topic explanation |
| LLM — cheap | claude-haiku | Guardrails classification, topic tagging at ingestion |
| Embeddings | Voyage AI voyage-large-2 | 1536d; strongest retrieval quality for math content |
| Frontend | React + Vite + KaTeX | Math rendering, SSE streaming display |
| Graphs | Desmos embed | Graph display in generated exams |
| Auth | fastapi-users + JWT | Registration, login, protected routes |
| Migrations | Alembic | Run-and-exit container; MUST complete before API starts |
| Containers | Docker Compose | Full-stack orchestration |

Services MUST communicate exclusively through domain models — ORM model instances MUST NOT cross
a layer boundary into `services/` or `api/`.

## Development Workflow

- Every feature MUST be developed on a named branch (e.g., `001-ingestion-pipeline`).
- The build order in `DECISIONS.md` Section 10 governs sequencing; deviations MUST be documented
  before work begins.
- The fallback order (Vault → `.env`, MinIO → local storage, etc.) defined in `DECISIONS.md`
  Section 10 MUST be applied in reverse priority when time constraints require scope reduction.
- All Docker Compose services MUST pass health checks before dependent services start.
- Constitution compliance MUST be verified at the start of each feature plan via the Constitution
  Check gate in `plan.md` before Phase 0 research proceeds.

## Governance

This constitution supersedes all inline code comments, ad-hoc decisions, and verbal agreements
regarding project architecture. Where a decision in `DECISIONS.md` conflicts with a principle here,
this constitution takes precedence and `DECISIONS.md` MUST be updated to reflect the resolution.

**Amendment procedure**: Any principle change MUST increment the version per semantic versioning
(MAJOR: principle removals or redefinitions; MINOR: new principles or sections; PATCH: wording
clarifications). The Sync Impact Report HTML comment MUST be updated and the amended constitution
committed before implementation proceeds.

**Compliance review**: The Constitution Check section of every `plan.md` MUST explicitly verify
each NON-NEGOTIABLE principle before Phase 0 research begins, and again after Phase 1 design.

**Version**: 1.0.0 | **Ratified**: 2026-06-03 | **Last Amended**: 2026-06-03
