# Contract: Chat (SSE)

The chat endpoint handles all AI coach interactions: topic explanations, on-demand reference
retrieval, curriculum-scope checks, and guardrails. All Claude responses stream via SSE.

**Auth**: Bearer required

---

## POST /chat

Send a student message and receive a streaming AI response.

**Auth**: Bearer required

**Request**:
```json
{
  "conversation_id": "<uuid>",
  "message": "Can you explain how to find horizontal asymptotes for rational functions?"
}
```

If `conversation_id` is omitted, a new conversation is created and its ID is included in the
first SSE event. Subsequent messages in the same session MUST include the same `conversation_id`.

**Response 200** — `Content-Type: text/event-stream`:

**Normal on-topic response**:
```
data: {"event": "conversation_id", "conversation_id": "<uuid>"}

data: {"event": "token", "text": "Horizontal asymptotes appear frequently in Lebanese GS exams..."}

data: {"event": "token", "text": " — in 8 of the last 10 exams, Functions included asymptote questions."}

data: {"event": "past_questions", "questions": [
  {"year": 2023, "session": 1, "content": "...", "marks": 2.0}
]}

data: {"event": "done"}

data: [DONE]
```

**Guardrails — drifting (2 consecutive off-topic messages)**:
```
data: {"event": "token", "text": "I can help with that briefly, but remember I'm here..."}

data: {"event": "guardrail_warning", "message": "Tip: I'm most useful for Lebanese GS Math exam prep. Try asking about a specific topic or past exam question."}

data: {"event": "done"}

data: [DONE]
```

**Guardrails — soft block (3+ consecutive off-topic messages)**:
```
data: {"event": "guardrail_block", "message": "I'm designed specifically for Lebanese GS Math exam preparation. Try asking me about Functions, Probability, Complex Numbers, or any other exam topic — or generate a practice exam!"}

data: [DONE]
```

No AI call is made when `guardrail_block` fires. The off-topic counter resets when the student
sends an on-topic message.

**Out-of-scope topic**:
```
data: {"event": "token", "text": "Oblique asymptotes are not part of the current year's GS Math curriculum (2024–2025). The curriculum only requires horizontal and vertical asymptotes. Here's what is in scope: ..."}

data: {"event": "done"}

data: [DONE]
```

**Response 503** — AI service unavailable (FR-026):
```json
{ "error": "Service temporarily unavailable. Please retry.", "request_id": "<uuid>" }
```

---

## SSE Event Reference

| Event | Payload fields | Description |
|---|---|---|
| `conversation_id` | `conversation_id` | Emitted first on a new conversation |
| `token` | `text` | Incremental Claude response token |
| `past_questions` | `questions[]` | Relevant past exam questions surfaced mid-response |
| `guardrail_warning` | `message` | Redirect reminder appended to drifting response |
| `guardrail_block` | `message` | Soft-block message — no AI content follows |
| `done` | — | AI response complete (stream still open) |
| `[DONE]` | — | SSE stream closing sentinel |

---

## Conversation Management

Conversation turns are persisted in the `messages` table. The `guardrails_score` field on each
`messages` row records the off-topic classification score (null for on-topic messages).

The off-topic counter is stored in Redis (`guardrails:{conversation_id}`, TTL 3h) and resets
to 0 when an on-topic message is received.
