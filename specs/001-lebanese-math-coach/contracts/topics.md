# Contract: Topic Analytics

Pure SQL queries on `topic_stats`. Zero LLM calls at runtime. All endpoints require Bearer auth.

---

## GET /topics/stats

Return all GS Math topics ranked by frequency of appearance across past official exams.

**Auth**: Bearer required

**Response 200**:
```json
{
  "topics": [
    {
      "topic": "Functions",
      "appearances": 24,
      "last_seen_year": 2026,
      "last_seen_session": 1,
      "frequency_tier": "high"
    },
    {
      "topic": "Probability",
      "appearances": 18,
      "last_seen_year": 2025,
      "last_seen_session": 2,
      "frequency_tier": "high"
    },
    {
      "topic": "Numerical Sequences",
      "appearances": 12,
      "last_seen_year": 2023,
      "last_seen_session": 1,
      "frequency_tier": "medium"
    }
  ]
}
```

Topics are ordered by `appearances DESC`. Frequency tier is computed server-side:
- `"high"`: appeared in ≥ 7 of the last 10 exam years
- `"medium"`: 4–6 of the last 10 exam years
- `"low"`: ≤ 3 of the last 10 exam years

This endpoint performs no AI processing and MUST respond in < 3 seconds.

---

## GET /topics/{topic}/questions

Return all past exam questions tagged with the given topic, ordered by most recent year first.

**Auth**: Bearer required

**Path param**: `topic` — exact topic name (URL-encoded if needed, e.g., `Complex%20Numbers`)

**Query params**:
- `year_from` (int, optional)
- `year_to` (int, optional)
- `question_type` (string, optional — `proof | calculation | mcq | sketch`)
- `limit` (int, optional, default 50, max 200)

**Response 200**:
```json
{
  "topic": "Functions",
  "total_returned": 12,
  "questions": [
    {
      "chunk_id": "<uuid>",
      "year": 2024,
      "session": 1,
      "subtopic": "Limits and Asymptotes",
      "question_type": "calculation",
      "marks": 3.0,
      "content": "Study the function f(x) = ...",
      "answer": "See official answer key: ..."
    }
  ]
}
```

**Response 404** — topic not found in topic_stats:
```json
{ "error": "Topic 'Topology' not found in the exam archive.", "request_id": "<uuid>" }
```
