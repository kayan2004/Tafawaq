# Contract: Exam Sessions

Covers session creation, active session retrieval, and session inspection.
All endpoints require Bearer token auth.

---

## POST /exams/generate

Generate a new mock exam session. Returns SSE stream of the exam content as it is generated.

**Auth**: Bearer required

**Request**:
```json
{ "session_type": "mock_generated" }
```

`session_type` must be `"mock_generated"` for AI-generated exams. Use `"real_past_exam"` for
past official exams (future endpoint, not in MVP scope).

**Response 200** — `Content-Type: text/event-stream`:
```
data: {"event": "session_created", "session_id": "<uuid>", "expires_at": "2026-06-03T13:00:00Z"}

data: {"event": "token", "text": "**Exercise 1 — Functions (4 points)**\n"}

data: {"event": "token", "text": "Let f(x) = ..."}

data: {"event": "exam_complete", "exam_content": { ...full ExamContent JSON... }}

data: [DONE]
```

The `exam_complete` event contains the full structured `exam_content` JSON (see data-model.md).
The answer key is stored server-side in Redis (`session:{id}`) and is never sent to the client.

**Response 409** — FR-024: student already has an active session:
```json
{
  "error": "You already have an active exam session. Submit or wait for it to expire before starting a new one.",
  "request_id": "<uuid>",
  "active_session_id": "<uuid>",
  "expires_at": "2026-06-03T13:00:00Z"
}
```

**Response 503** — AI service unavailable (FR-026):
```json
{
  "error": "Service temporarily unavailable. Please retry.",
  "request_id": "<uuid>"
}
```

---

## GET /exams/active

Return the current in-progress session for the authenticated student, if any.

**Auth**: Bearer required

**Response 200** — active session exists:
```json
{
  "session_id": "<uuid>",
  "session_type": "mock_generated",
  "status": "in_progress",
  "expires_at": "2026-06-03T13:00:00Z",
  "exam_content": { ...ExamContent JSON... }
}
```

**Response 404** — no active session:
```json
{ "error": "No active exam session found.", "request_id": "<uuid>" }
```

---

## GET /exams/{session_id}

Retrieve any exam session by ID (active, submitted, or graded). The answer key is never included
in this response.

**Auth**: Bearer required (must be the session owner)

**Response 200**:
```json
{
  "session_id": "<uuid>",
  "session_type": "mock_generated",
  "status": "graded",
  "created_at": "2026-06-03T10:00:00Z",
  "expires_at": "2026-06-03T13:00:00Z",
  "exam_content": { ...ExamContent JSON... }
}
```

**Response 404** — session not found or not owned by caller:
```json
{ "error": "Exam session not found.", "request_id": "<uuid>" }
```

**Response 410** — session expired:
```json
{ "error": "Exam session has expired.", "request_id": "<uuid>" }
```
