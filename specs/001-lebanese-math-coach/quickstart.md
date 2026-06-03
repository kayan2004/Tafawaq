# Quickstart: Lebanese Math Coach

How to bring the full stack up from scratch, verify every service is healthy, and confirm the
ingestion pipeline works before running the app.

---

## Prerequisites

- Docker Desktop (or Docker Engine + Compose v2) installed and running
- Git repository cloned
- Port availability: 8000 (API), 5173 (frontend dev), 5432 (Postgres), 6379 (Redis),
  9000/9001 (MinIO), 8200 (Vault)

---

## 1. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and set the Vault root token (the only secret that lives outside Vault in dev mode):

```env
VAULT_ADDR=http://vault:8200
VAULT_TOKEN=dev-root-token
```

All other credentials (Anthropic API key, Voyage AI key, DB password, MinIO access key) are
loaded into Vault in step 3.

---

## 2. Start infrastructure services

```bash
docker-compose up -d db redis minio vault
```

Wait ~5 seconds for Vault and Postgres to be ready, then verify:

```bash
docker-compose ps
# All four services should show "healthy" or "running"
```

---

## 3. Seed Vault with application secrets

```bash
docker-compose run --rm vault-seed
```

This one-shot container writes all application secrets to the Vault KV store at path
`secret/lebanese-math-coach`. It reads credentials from environment variables or a seed file.

Verify:
```bash
docker-compose run --rm vault sh -c \
  "vault kv get -address=http://vault:8200 secret/lebanese-math-coach"
# Should print all keys: anthropic_api_key, voyage_api_key, db_password, minio_access_key, etc.
```

---

## 4. Run database migrations

```bash
docker-compose run --rm migrate
# Should print: "INFO  [alembic.runtime.migration] Running upgrade -> 0001_baseline"
# Container exits with code 0
```

---

## 5. Start the API

```bash
docker-compose up api
```

The API container will:
1. Call `infra/vault.py:resolve_secrets()` — if Vault is unreachable, the process exits here
2. Load `app/data/curriculum.json` and few-shot exam files from `app/data/few_shot_exams/`
3. Pre-compute guardrail anchor embeddings (Voyage AI call)
4. Start serving on port 8000

Verify:
```bash
curl http://localhost:8000/health
# {"status": "ok", "vault": "connected", "db": "connected", "redis": "connected"}
```

---

## 6. Start the frontend (development)

```bash
cd frontend
npm install
npm run dev
# Vite dev server starts at http://localhost:5173
```

---

## 7. Run the ingestion pipeline (offline — run once before first use)

The ingestion pipeline processes past exam PDFs from MinIO into pgvector. It is not a runtime
service — run it once after the database is migrated.

**Step 1: Upload PDFs to MinIO**

```bash
# Copy your downloaded Apelr PDFs into a local directory, then:
docker-compose run --rm minio-seed
# Uploads all PDFs from ./data/pdfs/ to the MinIO bucket "past-exams"
```

**Step 2: Run ingestion**

```bash
docker-compose run --rm api python -m ingestion.pipeline
# Expected output:
# [ingestion] Processing GS_Math_2024_1_En.pdf...
# [ingestion] Extracted 23 chunks
# [ingestion] Tagged 23 chunks via claude-haiku
# [ingestion] Embedded 23 chunks via voyage-large-2
# [ingestion] Stored 23 chunks in pgvector
# [ingestion] Updated topic_stats (12 topics)
# ...
# [ingestion] Complete: 75 exams, 1,847 chunks total
```

Verify:
```bash
docker-compose exec db psql -U postgres -d lebanese_math \
  -c "SELECT COUNT(*) FROM chunks; SELECT COUNT(*) FROM topic_stats;"
# chunks: ~1800–2000 rows
# topic_stats: ~10–15 rows
```

---

## 8. End-to-end smoke test

```bash
# Register a student
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "testpass123"}'

# Login and get JWT
TOKEN=$(curl -s -X POST http://localhost:8000/auth/jwt/login \
  -F "username=test@example.com" -F "password=testpass123" \
  | jq -r '.access_token')

# Generate a mock exam (streaming)
curl -N -H "Authorization: Bearer $TOKEN" \
  -X POST http://localhost:8000/exams/generate \
  -H "Content-Type: application/json" \
  -d '{"session_type": "mock_generated"}' \
  | head -20
# Should see SSE data: {...} lines streaming in

# Check topic analytics (no AI — should be fast)
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/topics/stats
# Should return JSON array of topic objects with appearances + frequency_tier
```

---

## docker-compose.yml service summary

| Service | Port | Purpose | Health check |
|---|---|---|---|
| `api` | 8000 | FastAPI backend | `GET /health` |
| `db` | 5432 | PostgreSQL 16 + pgvector | `pg_isready` |
| `redis` | 6379 | Redis 7 | `redis-cli ping` |
| `minio` | 9000/9001 | MinIO object storage | `/minio/health/live` |
| `vault` | 8200 | HashiCorp Vault (dev mode) | `vault status` |
| `migrate` | — | Alembic run-and-exit | exits 0 on success |

`api` depends on: `db` (healthy), `redis` (healthy), `vault` (healthy), `migrate` (completed).

---

## Common issues

**API exits immediately at startup**: Vault is unreachable. Check `docker-compose ps vault`
and ensure the vault seed ran successfully in step 3.

**Chunks table empty after ingestion**: PDFs were not uploaded to MinIO (step 7, step 1).
Run `docker-compose run --rm minio-seed` and then re-run the pipeline.

**KaTeX not rendering in frontend**: Confirm the `frontend/` dev server is running on port 5173
and that the Vite proxy config points to `http://localhost:8000` for API calls.
