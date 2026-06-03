# Contract: Past Question Retrieval

Semantic search over the pgvector `chunks` table. All endpoints require Bearer token auth.

---

## POST /questions/retrieve

Retrieve past official exam questions by topic, question type, and/or year range using semantic
(cosine similarity) search via pgvector. Supports natural-language queries.

**Auth**: Bearer required

**Request**:
```json
{
  "query": "integration by parts questions from 2015 to 2024",
  "topic": "Integrals",
  "question_type": "calculation",
  "year_from": 2015,
  "year_to": 2024,
  "limit": 10
}
```

All fields except `query` are optional filters applied alongside semantic similarity. If only
`query` is provided, the system interprets it as a natural-language request and extracts topic,
question_type, and year range automatically via the `retrieve_past_questions` agent tool.

**Response 200**:
```json
{
  "total_returned": 8,
  "questions": [
    {
      "chunk_id": "<uuid>",
      "year": 2022,
      "session": 1,
      "topic": "Integrals",
      "subtopic": "Integration by Parts",
      "question_type": "calculation",
      "marks": 2.0,
      "content": "Calculate \\int x e^x \\, dx using integration by parts.",
      "answer": "xe^x - e^x + C",
      "similarity_score": 0.94
    }
  ]
}
```

`answer` is populated only when a matching answer-key chunk exists for the same year/session/part.
`similarity_score` is the cosine similarity (0–1; higher = more relevant).

**Response 200** — no results found:
```json
{
  "total_returned": 0,
  "questions": [],
  "suggestion": "No past questions found for this query. Try broadening the year range or topic."
}
```

**Response 503** — embedding service unavailable:
```json
{ "error": "Service temporarily unavailable. Please retry.", "request_id": "<uuid>" }
```
