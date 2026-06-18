# Guardrails redesign — design

## Context

The current guardrails system (`guardrails-service/` NeMo sidecar +
`app/services/guardrails_service.py`) is a single-purpose topic-relevance
filter: one custom NeMo action (`check_math_topic`) asks Claude Haiku
"is this on-topic for Lebanese GS Math?" and returns a boolean. A Redis
counter turns three consecutive off-topic messages into a block. There is
no prompt-injection detection, no general content-moderation, and the
admin "Guardrails" page is hardcoded to zeros because nothing persists
per-message verdicts (`messages.guardrails_score` exists but is never
written — confirmed dead in the prior services-layer audit).

This redesign generalizes the system into something closer to how
production chat apps actually do guardrails: a richer, multi-category
classifier; zero-tolerance handling for adversarial input distinct from
lenient handling of topic drift; real persistence wired into the
already-built admin UI; and PII-safe audit logging.

It also resolves, as a side effect, a previously-identified bug: the
guardrail block path in `chat_service.handle_turn` persisted a user
message with no paired assistant reply, breaking the Anthropic API's
required user/assistant alternation on the conversation's next turn. The
new design's rule — every block path persists a paired assistant message
— eliminates this independently of the redesign's other goals.

## Scope

**In scope:**
- Chat messages (`chat_service.handle_turn`) — input screening.
- Exam-generation brief (`exam_service.generate_exam`) — input screening.
- Exam-generation output — content-safety screening of the generated exam.
- Chat output — non-blocking, log-only content-safety audit.
- Admin Guardrails page — wired to real data (table already exists in the
  frontend, currently fed by hardcoded zeros).
- PII redaction of audit-log text previews via Presidio.

**Out of scope (explicitly deferred, not forgotten):**
- Vision-extracted handwritten exam answers (OCR'd during grading) — a
  real injection vector (affects scoring) but excluded from this pass per
  scope decision; revisit separately.
- Redacting live chat content (`messages.content`) — Presidio risks
  corrupting math notation (false positives on numeric/date-like
  patterns); redaction is audit-log-preview-only.
- NeMo's built-in `jailbreak_detection_heuristics` rail — investigated and
  rejected: requires `torch` + `transformers` + a 3GB `gpt2-large` download
  in the sidecar container, and its perplexity-based approach targets
  gibberish/adversarial-suffix attacks, not the natural-language injection
  ("ignore previous instructions") that is this app's actual threat model.
- NeMo's `self_check_input` built-in task — investigated and rejected as a
  *second* rail: its output parser is boolean-only (no category/score/
  reason), so it would add a redundant LLM call without adding signal
  beyond what the expanded custom action already produces.
- Grading-output (evaluator JSON) content screening — lower-value surface,
  highly constrained output format.

## Architecture

### Sidecar (`guardrails-service/`)

Keeps NeMo's `LLMRails`/flow framework — no new runtime dependencies. Two
custom actions, both single Claude Haiku calls:

**`classify_input`** (generalizes today's `check_math_topic`) — one call
per chat message / exam-generation brief, returns:
```json
{"category": "off_topic" | "prompt_injection" | "harmful_content" | null,
 "score": 0.0-1.0, "reason": "short phrase"}
```
The prompt covers all three categories in one pass: topic relevance
(existing logic), prompt-injection/jailbreak patterns (instruction
override attempts, role-play/"developer mode" framing, system-prompt
extraction attempts), and general harmful content (violence, self-harm,
hate, illegal activity).

**`classify_output`** (new, simpler) — checks the model's own generated
content for safety only, no adversarial-intent categories (they don't
apply to output):
```json
{"flagged": bool, "score": 0.0-1.0, "reason": "short phrase"}
```

`rails.co` gains two flows wrapping these actions; `/check` (input) and a
new `/check-output` endpoint on the sidecar's FastAPI app.

### Severity model

Two tiers, not one:

| Category | Tier | Behavior |
|---|---|---|
| `off_topic` | Lenient | Existing Redis counter: warning at 2 consecutive, block at 3. Unchanged shape. |
| `prompt_injection`, `harmful_content` | Zero-tolerance | Blocks that single message immediately. No counter, no grace period. |

## Data model

New enums in `app/domain/enums.py`:
```python
class GuardrailCategory(str, Enum):
    off_topic = "off_topic"
    prompt_injection = "prompt_injection"
    harmful_content = "harmful_content"

class GuardrailLevel(str, Enum):
    warned = "warned"
    blocked = "blocked"

class GuardrailSource(str, Enum):
    chat = "chat"
    exam_generation = "exam_generation"

class GuardrailDirection(str, Enum):
    input = "input"
    output = "output"
```

New table `guardrail_events` (decoupled from `messages` — exam-generation
blocks have no message row, so a dedicated table covers both surfaces
cleanly):

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `user_id` | UUID FK → users | always present |
| `conversation_id` | UUID FK → conversations, nullable | null for exam-generation source |
| `source` | `GuardrailSource` | |
| `direction` | `GuardrailDirection` | |
| `category` | `GuardrailCategory`, nullable | null only possible for flagged outputs (no category, just `flagged`) |
| `level` | `GuardrailLevel` | matches admin frontend's `"blocked"\|"warned"` literal exactly |
| `score` | float | |
| `reason` | text | |
| `text_hash` | string | SHA-256 of the full original (pre-redaction, pre-truncation) flagged text |
| `text_preview` | string(100) | truncated **and Presidio-redacted** — the only plaintext retained for this feature |
| `created_at` | timestamptz | |

Migration also **drops `messages.guardrails_score`** — confirmed dead in
the prior audit, now fully superseded by this table.

## Chat integration (`chat_service.handle_turn`)

After the user message is persisted (unchanged):

```python
verdict = await guardrails_service.classify_input(message)

if verdict.category in (PROMPT_INJECTION, HARMFUL_CONTENT):
    await message_repo.add_message(db_session, conversation_id, MessageRole.assistant, SAFETY_BLOCK_MESSAGE)
    await guardrails_service.log_event(db_session, source=CHAT, direction=INPUT, category=verdict.category,
                                        level=BLOCKED, score=verdict.score, reason=verdict.reason,
                                        text=message, user_id=user_id, conversation_id=conversation_id)
    await db_session.commit()
    yield block event (SAFETY_BLOCK_MESSAGE)
    return

if verdict.category == OFF_TOPIC:
    counter = await increment_counter(...)
else:
    await reset_counter(...); counter = 0
tier = get_guardrail_tier(counter)

if tier == "block":
    await message_repo.add_message(db_session, conversation_id, MessageRole.assistant, BLOCK_MESSAGE)
    await guardrails_service.log_event(..., category=OFF_TOPIC, level=BLOCKED, ...)
    await db_session.commit()
    yield block event
    return

if tier == "warning":
    await guardrails_service.log_event(..., category=OFF_TOPIC, level=WARNED, ...)
    # falls through to normal streaming response, unchanged
```

`SAFETY_BLOCK_MESSAGE` is a new constant in `prompts/math/chat.py`,
deliberately generic ("I can't help with that request") — it doesn't name
the detected category, so it gives an attacker no signal to calibrate
around. The existing friendly `BLOCK_MESSAGE` stays for off-topic.

**Invariant enforced everywhere:** every block path — zero-tolerance and
3-strike alike — persists a paired assistant message before returning.
This is what fixes the deferred orphaned-message bug.

After the turn's assistant message is committed (full streaming path),
fire a background task (own engine/sessionmaker, same pattern as
`exam_service._validate_exam_background`'s strong-ref task set so GC can't
collect it mid-run): `guardrails_service.audit_output_async(full_response,
...)` calls `classify_output` and logs a `WARNED`-level event if flagged.
Never blocks, never delays `[DONE]`.

## Exam-generation integration (`exam_service.generate_exam`)

**Input, before any side effect** (no archiving, no conversation/session
creation yet):
```python
if generation_prompt:
    verdict = await guardrails_service.classify_input(generation_prompt)
    if verdict.category in (PROMPT_INJECTION, HARMFUL_CONTENT):
        await guardrails_service.log_event(db_session, source=EXAM_GENERATION, direction=INPUT, ...,
                                             user_id=user_id, conversation_id=None)
        await db_session.commit()
        yield error event
        return
```
Only `prompt_injection`/`harmful_content` are checked — not `off_topic`.
An off-topic brief isn't a security concern (the system prompt already
constrains output to curriculum regardless, and `_validate_generated_payload`
catches structural drift); screening for it here would add cost for a
non-issue.

**Output, after `_validate_generated_payload` passes, before persisting
content and yielding `exam_complete`:**
```python
output_verdict = await guardrails_service.classify_output(_exam_content_as_text(exam_content))
if output_verdict.flagged:
    await guardrails_service.log_event(db_session, source=EXAM_GENERATION, direction=OUTPUT, level=BLOCKED,
                                        score=output_verdict.score, reason=output_verdict.reason,
                                        text=_exam_content_as_text(exam_content),
                                        user_id=user_id, conversation_id=conversation.id)
    await db_session.delete(placeholder_session)
    await db_session.commit()
    yield error event
    return
```
`_exam_content_as_text` is a new small helper (flattens the exam JSON's
exercise/part text into one string for classification) — `conversation`
already exists at this point (created earlier in the function), so unlike
the input check above, this event has a real `conversation_id`. Feasible
as a blocking check because this Claude call is not streamed — the full
exam text already exists in memory before anything is shown to the
student.

## Admin wiring

`admin_service.get_guardrails_summary()` / `get_guardrails_messages()`
(currently hardcoded) now query `guardrail_events`:

- **Summary**: `messages_7d` (unchanged, existing `admin_repo.count_messages`),
  `blocked`/`warned` = counts by `level` in the last 7 days, `block_rate` =
  blocked / messages_7d.
- **Messages**: rows from the last 7 days, newest first, mapped to
  `{ts, text: text_preview, score, level, reason}`.

This matches the **existing** `GuardrailsSummary` / `GuardrailMessage`
TypeScript interfaces in `admin/src/lib/api.ts` exactly — no frontend
changes needed.

## PII redaction

New `app/infra/pii_redaction.py` using `presidio-analyzer`, added to the
main `api` service's dependencies (not the sidecar — this runs where
`text_preview` is produced, avoiding an extra network hop).

Single choke point: `guardrails_service.log_event(...)` is the only way
any code path writes to `guardrail_events`. It hashes the original
full text (`text_hash`), truncates to 100 chars, redacts the truncated
preview through Presidio, and calls the repository insert. No caller can
forget redaction because no caller touches the table directly.

## Testing approach

Following this repo's established TDD practice (real Postgres via
`tests/conftest.py`, no mocking the DB):

- `guardrails_service.classify_input` / `classify_output` — unit tests
  against the parsing logic (JSON verdict → typed result), with the
  Claude call mocked (the only acceptable mock per TDD policy: an external
  paid API).
- `chat_service.handle_turn` block paths — integration test asserting a
  paired assistant message is always persisted (this is the regression
  test for the bug this redesign fixes).
- `guardrails_service.log_event` — integration test against the real DB
  asserting `text_preview` never contains a known PII pattern after
  redaction, and `text_hash` matches the un-redacted original.
- `admin_service.get_guardrails_summary/messages` — integration test
  seeding `guardrail_events` rows and asserting the returned shape exactly
  matches `GuardrailsSummary`/`GuardrailMessage`.

## Rollout

1. New Alembic migration: create `guardrail_events`, drop
   `messages.guardrails_score`.
2. Sidecar: update `rails.co`, `actions` (classify_input/classify_output),
   `main.py` (`/check-output` endpoint). No new sidecar dependencies.
3. Main API: new enums, new `guardrail_repo.py`, new `guardrails_service`
   functions, `presidio-analyzer` dependency, chat/exam-service wiring.
4. Rebuild and restart `guardrails` and `api` containers; verify both boot
   clean.
5. Manual verification: trip an off-topic 3-strike block, trip a
   prompt-injection zero-tolerance block, confirm the conversation
   recovers cleanly on the next turn (the bug-fix verification), confirm
   the admin Guardrails page shows real rows.
