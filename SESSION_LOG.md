# Session Log

Running log of notable work done across Claude Code sessions in this repo —
written so a session picking up later has full context without re-deriving
it from git history alone. Newest entries on top; append new entries above
older ones, separated by `---`.

---

## 2026-06-18 — Services-layer review: chat history window bug fixed, guardrail-orphan bug deferred

Continuation of the ongoing manual code audit (DB layer done previously, this
pass covered `app/services/` plus the `infra`/`ingestion` files referenced
from it). Two real bugs surfaced in the chat path; one fixed and verified
this session, one explicitly deferred per user decision.

### Bug fixed — `message_repo.get_messages()` returned the oldest N messages, not the most recent N

**Finding:** `get_messages()` ordered `created_at ASC` with `LIMIT`, no
offset — always the *first* N messages ever written to a conversation, not
a sliding window. Both call sites affected: `chat_service.handle_turn()`
(`limit=20`, builds the actual Claude context) and the chat-history-display
router (`limit=100`). Once a conversation passed 20 messages (10 turns),
every later message — including the user's current question, just
persisted before this call — fell outside "oldest 20" and was silently
dropped from what's sent to Claude. The model would keep answering based on
the first 10 exchanges forever.

**User decision:** Fix this one now; leave the second bug (below) for later.

**Fix:** `app/repositories/message_repo.py` — `get_messages()` now orders
`created_at DESC` + `LIMIT`, then reverses in Python to restore chronological
order for the caller.

**TDD:** Added `tests/conftest.py` (first test infra in this repo — real
Postgres via `TEST_DATABASE_URL`/local dev DB at `localhost:5432`, no SQLite
per CLAUDE.md) and `tests/repositories/test_message_repo.py`. Test inserts 25
messages (committing after each, matching production's per-message commit
pattern — Postgres `now()` is transaction-scoped, so distinct transactions
are required for distinct timestamps), asserts `get_messages(limit=20)`
returns `msg-5..msg-24`. Watched it fail against the old ASC+LIMIT code
(returned `msg-0..msg-19`) before fixing.

**Verified:** Test passes. `docker compose build api && docker compose up -d
api` — container rebuilt (no live source mount on this service) and boots
clean.

### Bug found, deferred — guardrail block leaves an orphaned user message

**Finding:** In `chat_service.handle_turn()`, the user's message is
persisted unconditionally before the guardrail tier check. When
`tier == "block"` (3rd consecutive off-topic message), the function returns
right after yielding the block SSE event — no assistant message is ever
persisted for that turn. Anthropic's Messages API requires strict
user/assistant alternation (`claude.py`'s `stream_claude`/`call_claude` pass
`messages` straight through, no coalescing). The next turn rebuilds
`claude_messages` from history and gets two consecutive user-role messages
→ `APIStatusError` → `AIServiceUnavailable`. The window fix above does
**not** self-heal this: the failed recovery attempt's user message also
never gets an assistant reply persisted (the exception skips the line 318
persist), so it orphans too — each retry adds another orphan to the tail
instead of fixing the alternation. The conversation stays broken
(every turn 400s) until `clear_chat` resets it via `cleared_at`; that's the
only recovery path. The 400 also fires mid-stream (SSE already at 200), so
per CLAUDE.md rule 6 it can't map to a clean 4xx — the user just sees the
stream break.

**Repro:** 3 off-topic messages in a row (trips block), then 1 on-topic
message — that 4th call is expected to fail, and so is every call after it
until the chat is cleared.

**User decision:** Deferred — not fixed this session. `admin_service.py`
already has a comment noting guardrails is getting a larger rework later;
this fits naturally into that future work rather than a standalone patch.

### Other findings this session (doc-only, no functional impact — not actioned)

- CLAUDE.md's `infra/` listing omits `evaluator.py`, `tts.py`, `email.py`
  (all real, in-use files); its router list omits `official_exams.py`,
  `tts.py`, `user_details.py`, `admin.py`; "MinIO ... not yet used by
  runtime code" is no longer true (`grading_service` reads PDFs from it,
  `tts_service` uses it as an audio cache); ingestion section omits
  `book_ingest.py`, `topic_tagging.py`, `pipeline.py`, `chunker.py`,
  `embedder.py`, `pdf_extractor.py`, `tagger.py`.
- `grading_service._fetch_pdf` hardcodes its own `Minio(...)` client instead
  of reusing `minio_client.get_minio_client(secrets)`.
- `evaluator.py`'s `call_evaluator`/`call_pdf_evaluator` have near-identical
  JSON-parsing/exception blocks.
- `chat_service`'s tool-call loop caps at 4 rounds; if round 4 still returns
  a tool call, the tool runs but no follow-up call lets Claude use the
  result — response would end abruptly. Rare given only one tool is active.

---

## 2026-06-18 — Database audit: dead columns, dead TTL path, missing last_login

Originated from a full database audit ("check the db as a whole for unused
or bad-practice columns/tables") that surfaced four issues. All four were
fixed, migrated against the live dev DB, verified end-to-end, and committed
as three separate commits on `main`.

### Commits

| SHA | Subject |
|---|---|
| `ba6b3cb` | fix(db): drop dead chunks columns and join |
| `505a86a` | fix(db): drop exam_sessions.expires_at and dead Redis session read path |
| `aada81a` | fix(auth): record last_login on successful sign-in |

(Preceding context: `8f29fee` admin panel, `42f0839` topic_stats fix — earlier
work in the same audit, already committed before this summary's scope.)

---

### Issue 1 — `exam_sessions.expires_at` (commit `505a86a`)

**Finding:** Column was hardcoded to a year-2099 sentinel
(`_FAR_FUTURE = datetime(2099, 12, 31, ...)`) in `exam_repo.create_session()`,
never read by any query. CLAUDE.md falsely documented a 3-hour TTL.

**Also found while investigating:** `redis_client.get_session()` and
`delete_session()` (the read/delete halves of a Redis-backed session
mirror) had zero callers anywhere in the codebase. Only `set_session()`
(the write) is called — from `exam_service.py` and
`official_exam_service.py`. Grading reads the answer key directly from
Postgres via a same-named but distinct `get_session` in `exam_repo.py`
(SQLAlchemy-based, unrelated to Redis).

**User decision (asked via clarifying question):** Remove the column +
the dead Redis read path entirely.

**Changes:**
- `alembic/versions/0011_drop_exam_sessions_expires_at.py` — new migration, `drop_column`/`add_column` pair.
- `app/repositories/orm.py` — removed `expires_at` from `ExamSessionORM`.
- `app/repositories/exam_repo.py` — removed `_FAR_FUTURE` constant and its use in `create_session()`.
- `app/infra/redis_client.py` — removed `get_session()`/`delete_session()`. Kept `set_session()` (still called, even though its write now feeds an unread key — flagged as out-of-scope, see below).
- `CLAUDE.md` — `exam_sessions` table row now says "Permanent — no expires_at" (matches `exam_results`); Redis keys section rewritten to honestly describe `session:{id}` as write-only/unconsumed.

**Verified:** `\d exam_sessions` post-migration shows no `expires_at` column; `alembic_version` = `0011`; API rebuilt and booted clean.

---

### Issue 2 — `chunks.subtopic`, `page_start`, `page_end` + dead join (commit `ba6b3cb`)

**Finding:** `chunks.subtopic` always `''` (set via `tagger.py`'s
`chunk.setdefault("subtopic", "")`, never populated with real data, zero
frontend consumers) — same dead-data pattern as the already-fixed
`topic_stats.subtopic` column from earlier in this audit.
`chunks.page_start`/`page_end` always `NULL` since textbook content
stopped being chunked/embedded (textbook retrieval moved to direct
page-number lookup against `textbook_pages`). `chunk_repo.cosine_similarity_search`
still had a `LEFT JOIN textbook_pages tp ON tp.page_number = c.page_start`
and selected `c.subtopic, c.page_start, c.page_end, tp.chapter, tp.section`
— entirely dead.

**User decision:** Drop `subtopic` (asked explicitly, chose "Drop it").
`page_start`/`page_end` were dropped without a separate question — treated
as unambiguous since they were the literal subject of the dead-join finding,
and the user had already approved the identical "drop dead column" pattern
twice this session (`topic_stats.subtopic`, then `chunks.subtopic`).

**Changes:**
- `alembic/versions/0010_drop_chunks_dead_columns.py` — new migration, drops all three columns with a matching `downgrade()`.
- `app/repositories/orm.py` — removed `subtopic`, `page_start`, `page_end` from `ChunkORM`.
- `app/repositories/chunk_repo.py` — `cosine_similarity_search()` SELECT trimmed, dead `LEFT JOIN` removed.
- `app/domain/models.py` — removed `subtopic` field from `PastQuestion`.
- `app/services/retrieval_service.py`, `app/services/topic_service.py` — removed `subtopic=...` from `PastQuestion(...)` construction.
- `ingestion/pipeline.py` — `insert_chunks()` INSERT column list/placeholders renumbered, `subtopic` removed from upsert tuple and `ON CONFLICT` clause.
- `ingestion/tagger.py` — removed `chunk.setdefault("subtopic", "")`; docstring updated.
- `CLAUDE.md` — `chunks` row description trimmed; `textbook_pages` row note corrected to "looked up directly by page_number, not joined from chunks".

**Verified:** `\d chunks` post-migration shows exactly `id, source_type, year, session, exercise_id, topic, question_type, marks, content, embedding, created_at`. Live-executed `cosine_similarity_search` with a dummy 1536-dim zero vector — returned 3 rows with the trimmed field set.

---

### Issue 3 — `users.last_login` never written (commit `aada81a`)

**Finding:** Displayed on the admin Users page but never written anywhere —
0 of 14 users had it set.

**User decision:** Record it on login (recommended option), matching the
existing `on_after_register`/`on_after_forgot_password` hook pattern already
in `UserManager`.

**Changes:**
- `app/infra/auth.py` — added `on_after_login(user, request, response)` to `UserManager`, calling `await self.user_db.update(user, {"last_login": datetime.now(timezone.utc)})`. fastapi-users 13.x invokes this automatically after a successful `/auth/jwt/login`, never on failed auth (confirmed by reading the installed library source).

**Verified two ways:**
1. Direct method call against the real `test@test.com` user row inside the running container — `last_login` went from `NULL` to a real timestamp.
2. **Full HTTP round trip** (closed a gap flagged by review): registered a throwaway user via `POST /auth/register`, confirmed `last_login` was `NULL`, called `POST /auth/jwt/login` with real credentials, got a JWT back, re-queried Postgres — `last_login` flipped to `2026-06-18 12:36:57.372395+00`. Throwaway user deleted afterward.

---

### Explicitly out-of-scope (found, not touched)

- **`redis_client.set_session`** — still writes the Redis `session:{id}` mirror on exam creation even though nothing reads it back (the read half was removed in Issue 1). Kept because it's still actively called and removing it wasn't part of the approved scope. Candidate for a future cleanup if the mirror is ever proven truly unnecessary.
- **`ActiveSessionExists` / `SessionExpired`** (`app/domain/exceptions.py`, handlers in `app/api/exceptions.py`) — dead exception classes, never raised anywhere in services. `ActiveSessionExists` still takes/serializes an `expires_at` field, now an orphaned concept post-Issue-1. Harmless (handler never fires) but latent debt. Not part of any approved question/answer this session.
- **`app/repositories/admin_repo.py`, `admin_service.py`, `api/routers/admin.py`** — confirmed via grep to never reference any of the removed columns; unaffected.
- **`app/repositories/topic_stats_repo.py`** — confirmed to only use `ChunkORM.source_type/topic/year/session/question_type`; unaffected by column removal.
- **`ingestion/chunker.py`, `ingestion/embedder.py`** — confirmed via grep to never set `subtopic`/`page_start`/`page_end`.

### Environment notes for continuation

- All migrations (`0009` → `0010` → `0011`) are applied to the live dev DB; `alembic_version` = `0011`.
- The `api` container has been rebuilt and restarted with all code changes; boots clean.
- The `migrate` Compose service is `build: .` with no live source mount — after pulling these commits elsewhere, run `docker compose build migrate` before `docker compose run --rm migrate`, or a stale image will fail with "Can't locate revision."
- No ingestion pipeline run was triggered by any of this work (no Claude/Voyage/Haiku API calls made).
