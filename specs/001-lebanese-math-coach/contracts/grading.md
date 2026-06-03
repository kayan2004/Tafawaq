# Contract: Grading & Results

Covers answer submission, dual evaluation results, and permanent results history.
All endpoints require Bearer token auth.

---

## POST /exams/{session_id}/submit

Submit student answers for evaluation. Triggers the dual evaluator (two parallel AI calls).
Returns SSE stream of grading progress and final results.

**Auth**: Bearer required (must be session owner)

**Request**:
```json
{
  "answers": [
    {
      "exercise_id": 1,
      "parts": [
        {
          "part": "1",
          "answer": "lim = 0 because e^{-x} approaches infinity as x → -∞",
          "submitted_at": "2026-06-03T10:23:00Z"
        }
      ]
    }
  ]
}
```

**Response 200** — `Content-Type: text/event-stream`:
```
data: {"event": "evaluating", "message": "Grading your submission..."}

data: {"event": "evaluator_1_complete", "evaluator": { ...EvaluatorScore JSON... }}

data: {"event": "evaluator_2_complete", "evaluator": { ...EvaluatorScore JSON... }}

data: {"event": "grading_complete", "result": { ...EvaluationResult JSON... }}

data: [DONE]
```

Both evaluators run in parallel. The `grading_complete` event contains the full
`EvaluationResult` including `discrepancy_flagged` and `discrepancy_details`
(see data-model.md for full shapes). Results are saved to `exam_results` (permanent — FR-025).

**Response 404** — session not found:
```json
{ "error": "Exam session not found.", "request_id": "<uuid>" }
```

**Response 409** — session already submitted:
```json
{ "error": "This exam session has already been submitted.", "request_id": "<uuid>" }
```

**Response 410** — session expired:
```json
{ "error": "Exam session has expired.", "request_id": "<uuid>" }
```

**Response 422** — invalid answer payload:
```json
{ "error": "Invalid answer submission: exercise_id 5 not found in exam.", "request_id": "<uuid>" }
```

**Response 503** — AI service unavailable (FR-026):
```json
{
  "error": "Service temporarily unavailable. Please retry.",
  "request_id": "<uuid>"
}
```

---

## GET /exams/{session_id}/results

Retrieve evaluation results for a submitted or graded session.

**Auth**: Bearer required (must be session owner)

**Response 200**:
```json
{
  "session_id": "<uuid>",
  "total_score_1": 14.5,
  "total_score_2": 15.0,
  "discrepancy_flagged": true,
  "discrepancy_details": "Exercise 1 part 2 score differs by 0.5 points",
  "evaluator_1": {
    "scores": { "Q1_1": 2.0, "Q1_2": 0.5 },
    "total": 14.5,
    "feedback": "Good understanding of limits. Missing asymptote conclusion in Q1.2.",
    "missing_keywords": ["horizontal asymptote"]
  },
  "evaluator_2": {
    "scores": { "Q1_1": 2.0, "Q1_2": 1.0 },
    "total": 15.0,
    "feedback": "Strong work. Limit calculation correct. Minor omission in asymptote notation.",
    "missing_keywords": []
  }
}
```

**Response 404** — session not found or results not yet available:
```json
{ "error": "Results not found. Has the exam been submitted?", "request_id": "<uuid>" }
```

---

## GET /exams/history

Return all past evaluation results for the authenticated student, ordered by most recent first.
Results are permanent — no expiry (FR-025).

**Auth**: Bearer required

**Query params**:
- `limit` (int, optional, default 20, max 100)
- `offset` (int, optional, default 0)

**Response 200**:
```json
{
  "total": 7,
  "results": [
    {
      "result_id": "<uuid>",
      "session_id": "<uuid>",
      "session_type": "mock_generated",
      "created_at": "2026-06-03T10:45:00Z",
      "total_score_1": 14.5,
      "total_score_2": 15.0,
      "discrepancy_flagged": true
    }
  ]
}
```

Each item is a summary. Retrieve full detail via `GET /exams/{session_id}/results`.
