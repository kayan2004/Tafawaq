# Lebanese Math Exam AI Coach — Project Decisions & Features

> **Author:** Kayan Abdulbaki  
> **Subject:** GS Grade 12 Mathematics  
> **Timeline:** 2 weeks  
> **Stack:** FastAPI + pgvector + Redis + MinIO + Vault + React + Docker Compose + Claude API

---

## 1. SUBJECT & DATA

### Subject
- **GS Grade 12 Mathematics** (General Sciences track)
- Exams are in **English** (English track — separate exam from French track, same curriculum)
- Math notation extracts cleanly from Apelr PDFs as readable Unicode text

### Data Sources
| Source | Content | Format | Status |
|---|---|---|---|
| Apelr | 75 past official GS Math exams + answer keys (2000–2026) — English track (`_En` files) | PDF | Ready to download |
| Manual | Curriculum JSON — created by Kayan | JSON | To be created |
| CRDP app | Lebanese Math textbook (Building Up Mathematics) | PDF (if clean) | Optional — v2 |

### Why GS Grade 12 Math
- Strongest personal domain knowledge → can validate outputs
- 75 confirmed clean PDFs with structured answer keys
- English track → clean embeddings, no mixed-language issues, strongest LLM performance
- Complex enough to justify RAG and domain-specific grounding
- Exam structure is highly consistent year to year → easy to pattern match

---

## 2. ARCHITECTURE DECISIONS

### Overall Pattern
- **System prompt** handles exam structure, instructor persona, rubric behavior, and language
- **RAG is used surgically** — only when retrieval genuinely adds value, not on every call
- **Few-shot examples** from 2–3 most recent English track full past exams baked into system prompt
- **On-demand tool calling** — LLM decides when to retrieve, not always-on RAG
- **Streaming** — all Claude responses streamed to frontend via SSE

### RAG Usage Map
| Feature | Mechanism | Reason |
|---|---|---|
| Exam generation | System prompt + few-shot past exam examples | Structure is static, fits in context window |
| Curriculum scoping | Curriculum JSON injected into system prompt | Small enough to inject directly |
| Topic explanation | RAG retrieves relevant past exam questions on same topic | Textbook ingestion deferred to post-MVP |
| Past question retrieval | RAG semantic search | Core retrieval use case |
| Grading — real past exam | RAG retrieves official answer key | Actual document needed |
| Grading — generated exam | Answer key generated alongside exam, stored in Redis | No document to retrieve |
| Topic analytics | Postgres query on pre-tagged topic metadata | Pure analytics, no LLM needed at runtime |

### Agent Tools (3 tools only)
| Tool | Trigger | Returns |
|---|---|---|
| `retrieve_past_questions(topic, question_type, year_from, year_to)` | Style grounding, topic explanation, student retrieval queries | Ranked past question/answer pairs |
| `retrieve_answer_key(year, session, exercise_id)` | Grading real past exam | Official answer key chunks |
| `get_topic_stats(topic)` | Frequency context in explanations, exam generation weighting | Appearance count, last seen year |

### Multi-Agent Pattern
- **Dual evaluator** is the only justified multi-agent use
- Two independent Claude API calls with deliberately different system prompts
- Evaluator 1: strict Lebanese examiner (deducts on doubt)
- Evaluator 2: lenient Lebanese examiner (awards on doubt)
- Both run in parallel, results compared and displayed side by side
- Mirrors real Lebanese grading where two independent correctors grade the same paper

### Why Not Fine-Tuning
- Fine-tuning teaches style, not knowledge
- Lebanese curriculum changes yearly — fine-tuned knowledge goes stale
- Insufficient data (75 past exams is not enough for meaningful fine-tuning)
- RAG is strictly better for document-grounded responses

---

## 3. TECH STACK

| Component | Technology | Purpose |
|---|---|---|
| Backend | FastAPI (Python) | Core API, RAG logic, LLM orchestration |
| Vector DB | pgvector + PostgreSQL 16 | Embeddings + structured metadata + topic tags |
| Object storage | MinIO | Raw PDF storage for past exams |
| Session memory | Redis | Active exam sessions, generated answer keys, guardrails scores |
| Secrets | Vault | Anthropic API key, Voyage AI key, DB credentials, MinIO credentials |
| LLM — generation/grading | claude-sonnet-4-5 | Exam generation, dual evaluation, explanations |
| LLM — cheap tasks | claude-haiku | Guardrails classification, topic tagging at ingestion |
| Embeddings | Voyage AI — voyage-large-2 (1536 dimensions) | Vectorization of chunks |
| Frontend | React + Vite + KaTeX | Student UI, math rendering, streaming display |
| Graphs | Desmos embed | Graph display in generated exams |
| Auth | fastapi-users + JWT | User registration, login, protected routes |
| Migrations | Alembic | Database schema versioning |
| Containers | Docker Compose | Full stack orchestration |

### Container Services
```
docker-compose up
├── api          (FastAPI backend)
├── db           (postgres:16 + pgvector)
├── redis        (redis:7)
├── minio        (minio/minio)
├── vault        (hashicorp/vault dev mode)
└── migrate      (alembic upgrade head — exits after running)
```

### Codebase Structure (layered — same standard as Week 7)
```
app/
├── api/          HTTP only — routers, no business logic
├── services/     Business logic, transaction boundaries
├── repositories/ SQL only — no HTTP errors, no cache
├── domain/       Pydantic domain models (distinct from ORM)
└── infra/        Vault, MinIO, Redis, LLM, Voyage AI adapters
```

---

## 4. DATABASE SCHEMA

### PostgreSQL Tables

**users**
```
id: uuid (PK)
email: varchar (unique)
hashed_password: varchar
is_active: boolean
is_superuser: boolean
created_at: timestamp
last_login: timestamp
```

**conversations**
```
id: uuid (PK)
user_id: uuid (FK → users)
created_at: timestamp
last_message_at: timestamp
```

**messages**
```
id: uuid (PK)
conversation_id: uuid (FK → conversations)
role: enum (user, assistant)
content: text
created_at: timestamp
guardrails_score: float (nullable)
```

**exam_sessions**
```
id: uuid (PK)
conversation_id: uuid (FK → conversations)
user_id: uuid (FK → users)
session_type: enum (mock_generated, real_past_exam)
exam_content: jsonb
answer_key: jsonb
status: enum (in_progress, submitted, graded)
created_at: timestamp
expires_at: timestamp
```

**exam_results**
```
id: uuid (PK)
session_id: uuid (FK → exam_sessions)
user_id: uuid (FK → users)
student_answers: jsonb
evaluator_1: jsonb
evaluator_2: jsonb
total_score_1: float
total_score_2: float
discrepancy_flagged: boolean
image_path: varchar (nullable — for future handwritten upload)
created_at: timestamp
```

**chunks** (pgvector)
```
id: uuid (PK)
source_type: enum (past_exam, answer_key)
year: int
session: int
topic: varchar
subtopic: varchar
question_type: enum (proof, calculation, mcq, sketch)
marks: float
content: text
embedding: vector(1536)
created_at: timestamp
```

**topic_stats**
```
id: uuid (PK)
topic: varchar
subtopic: varchar
appearances: int
last_seen_year: int
last_seen_session: int
```

### Redis Keys
```
session:{session_id}     → active exam content + answer key (TTL: 3 hours)
guardrails:{session_id}  → consecutive off-topic message counter (TTL: 3 hours)
```

### jsonb Structures

**exam_content**
```json
{
  "exercises": [
    {
      "id": 1,
      "topic": "Functions",
      "total_marks": 4,
      "content": "Let f(x) = \\frac{2}{1 - xe^{-x}}...",
      "graph": {
        "type": "desmos",
        "expression": "y = 2 / (1 - x * e^{-x})",
        "x_range": [-6, 8],
        "y_range": [-4, 4]
      },
      "parts": [
        {
          "part": "1",
          "marks": 1,
          "content": "Determine \\lim_{x \\to -\\infty} f(x)"
        }
      ]
    }
  ]
}
```

**student_answers**
```json
{
  "answers": [
    {
      "exercise_id": 1,
      "parts": [
        {
          "part": "1",
          "answer": "lim = 0 because e^{-x} approaches infinity",
          "submitted_at": "2024-07-03T10:23:00"
        }
      ]
    }
  ]
}
```

**evaluator output**
```json
{
  "exercise_1": {
    "parts": {
      "1": {
        "score": 0.75,
        "max_score": 1,
        "feedback": "Correct limit but missing asymptote conclusion",
        "missing_keywords": ["horizontal asymptote"]
      }
    },
    "exercise_total": 0.75,
    "exercise_max": 4
  }
}
```

---

## 5. INGESTION PIPELINE

### Document Types in Vector Store
| Collection | Content | Chunking Strategy |
|---|---|---|
| past_exams | Questions from Apelr PDFs | Fixed size (500–800 tokens) with 100 token overlap |
| answer_keys | Official solutions with marks per part | Fixed size with overlap, tagged by question |

### Ingestion Flow
```
PDF downloaded from Apelr
  → stored in MinIO
  → pdfplumber extracts text
  → chunked (fixed size + overlap)
  → claude-haiku assigns topic + subtopic + question_type
  → Voyage AI voyage-large-2 generates embeddings
  → stored in pgvector with metadata
  → topic_stats table updated
```

### Topic Tagging (at ingestion time)
- claude-haiku reads each chunk and assigns topic + subtopic from predefined topic list
- Tags stored in Postgres alongside vector embeddings
- Enables topic frequency analytics without any runtime LLM calls
- Diagram images in past exam PDFs: text only — images skipped

### Filename Convention (Apelr)
```
GS_Math_{year}_{session}_En.pdf   → past exam
GS_Math_{year}_{session}_En_AK.pdf → answer key
```

---

## 6. CORE FEATURES

### Feature 1 — Mock Exam Generation
- Generates a full Lebanese GS Math exam following official structure exactly
- All questions are obligatory — no student choice, number of questions varies by year
- Structure follows most recent year's exam but with some leniency
- Grounded in few-shot examples from 2–3 most recent English track past exams
- Scoped to current year curriculum via injected JSON
- LLM generates the exam **and** the answer key simultaneously
- Answer key stored in Redis for the session duration (TTL: 3 hours)

### Feature 2 — Dual AI Evaluator
- Mirrors real Lebanese grading: two independent instructors grade same submission
- Two separate claude-sonnet-4-5 API calls run in parallel
- Evaluator 1 system prompt: strict Lebanese examiner — deducts on doubt
- Evaluator 2 system prompt: lenient Lebanese examiner — awards on doubt
- Each evaluator returns: score per part, total score, feedback, missing keywords
- Results compared and displayed side by side
- Discrepancies flagged to the student

### Feature 3 — Past Question Retrieval
- Student queries: "Give me all integration questions from 2015–2024"
- Semantic search via pgvector returns ranked relevant past questions
- Results include year, session, marks, and official answer
- Handles natural language queries accurately

### Feature 4 — Topic Frequency Analytics
- Dashboard showing all GS Math topics ranked by appearance frequency across years
- Color coded: red = high frequency (≥7/10 years), yellow = medium, green = low
- "Last seen" column — e.g. "Numerical Sequences last appeared in 2023"
- Clicking a topic → shows all past questions on that topic
- Computed entirely from Postgres topic_stats — zero LLM calls at runtime

### Feature 5 — Curriculum-Aware Responses
- Curriculum JSON defines which topics and subtopics are in scope for the current year
- Injected into every system prompt — LLM respects scope boundaries
- Curriculum JSON updatable yearly without touching any code

**Curriculum JSON Structure:**
```json
{
  "subject": "Mathematics",
  "track": "GS",
  "language": "English",
  "year": "2024-2025",
  "topics": [
    {
      "chapter": 1,
      "title": "Functions and Limits",
      "subtopics": ["Limits", "Continuity", "Asymptotes"],
      "included": true,
      "lebanese_specific_notes": "Only horizontal and vertical asymptotes required. Oblique asymptotes are out of scope."
    }
  ]
}
```

### Feature 6 — Topic Explanation (RAG-grounded)
- Student asks about a topic → RAG retrieves relevant past exam questions on same topic
- Explanation grounded in how Lebanese examiners actually test this topic
- After explanation: surfaces 2–3 real past exam questions on same topic
- Includes topic frequency context: "This topic appeared in 8 of the last 10 exams"
- Note: textbook-grounded explanations deferred to post-MVP (see B5)

### Feature 7 — On-Demand Reference Tool
- LLM has tool: `retrieve_exam_reference(topic, question_type)`
- Called automatically when LLM is uncertain how a question type should be answered
- Retrieves relevant past question/answer pairs from vector store
- Grounds response in official Lebanese exam style — not general math conventions

### Feature 8 — Student Answer Submission
- Student types answers directly in the app — plain text input (no LaTeX required from student)
- Questions displayed to student with KaTeX rendering
- Answer submitted per question or as full exam
- Evaluator receives: question, student answer, generated answer key, rubric

### Feature 9 — Guardrails & Session Scoring
**Architecture:**
- First message (>10 words): cosine similarity check against math education anchor embeddings
- First message (<10 words): pass through to system prompt guardrail
- Subsequent messages: system prompt guardrail only
- Session score tracked in Redis using consecutive off-topic message counter

**Three response tiers:**
| Session state | Action |
|---|---|
| On-topic | Proceed normally |
| Drifting (2 consecutive off-topic) | Add gentle redirect reminder to system prompt |
| Off-topic (3+ consecutive) | Soft block with redirect message |

---

## 7. EXAM STRUCTURE (Lebanese GS Math)

```
Total: 20 points
Questions are obligatory — no choice given to student
Number of questions varies by year
Duration: 3 hours
Language: English (English track)
Non-programmable calculator allowed

Question types observed across past exams:
- Functions and Complex Numbers (MCQ format)
- Probability
- Complex Numbers
- Transformations
- Functions (curve study)
- Numerical Sequences and Integrals
```

---

## 8. GRADING DESIGN

### For Real Past Official Exams
- Official answer key retrieved from vector store via RAG (Tool 2)
- Graded against official marks per sub-question
- Partial credit follows official rubric exactly

### For Agent-Generated Exams
- Answer key generated simultaneously with exam
- Stored in Redis under session ID (TTL: 3 hours)
- Retrieved at grading time — no RAG needed

### Dual Evaluator Output Format

Each evaluator returns per-exercise, per-part results. `grand_total` and `grand_max` are computed
in Python from the exercises array (not trusted from Claude). Discrepancy is flagged when
`abs(grand_total_1 - grand_total_2) >= 2.0`.

```json
{
  "session_id": "uuid",
  "evaluator_1": {
    "exercises": [
      {
        "exercise_id": 1,
        "parts": {
          "1)": { "score": 1.5, "max_score": 2.0, "feedback": "" },
          "2)": { "score": 0.75, "max_score": 1.0, "feedback": "Missing justification" }
        },
        "exercise_total": 2.25,
        "exercise_max": 3.0
      }
    ],
    "grand_total": 14.5,
    "grand_max": 20.0
  },
  "evaluator_2": {
    "exercises": [ "..." ],
    "grand_total": 15.0,
    "grand_max": 20.0
  },
  "discrepancy_flagged": false,
  "discrepancy_details": null,
  "average_total": 14.75
}
```

Grading is triggered via `POST /grade` with `{ session_id, answers }` — returns JSON directly
(non-streaming). Both evaluators run in parallel via `asyncio.gather`.

---

## 9. MODEL USAGE MAP

| Task | Model | Reason |
|---|---|---|
| Exam generation | claude-sonnet-4-5 | Accuracy critical |
| Dual evaluator (both) | claude-sonnet-4-5 | Accuracy critical |
| Topic explanation | claude-sonnet-4-5 | Quality matters |
| On-demand reference tool | claude-sonnet-4-5 | Quality matters |
| Guardrails classification | claude-haiku | Simple classification, cost efficiency |
| Topic tagging at ingestion | claude-haiku | Batch processing, cost efficiency |
| Embeddings | voyage-large-2 (1536d) | Best retrieval quality for math content |

---

## 10. BUILD ORDER (2 Weeks)

### Week 1 — Core Pipeline
| Day | Task |
|---|---|
| 1–2 | Docker Compose setup: all services + Vault wired + Alembic baseline |
| 3 | PDF ingestion pipeline: download Apelr exams, extract, chunk, embed, store |
| 4 | RAG retrieval working: query pgvector, return relevant past questions |
| 5 | Exam generation: Claude API + system prompt + few-shot examples |

### Week 2 — Evaluator + UI + Polish
| Day | Task |
|---|---|
| 1–2 | Dual evaluator: answer key generation + parallel grading logic |
| 3 | React frontend: exam display with KaTeX, answer submission, results |
| 4 | Topic analytics: frequency query from Postgres, dashboard display |
| 5 | Guardrails + session scoring + curriculum JSON + demo prep |

### Fallback Order (if time runs short, drop in this order)
1. Vault → replace with `.env`
2. MinIO → replace with local file storage
3. Topic analytics UI → keep data, skip visualization
4. Dynamic session scoring → replace with system prompt only
5. Users + auth → anonymous sessions only

---

## 11. BONUS — POST-MVP FEATURES

### B1 — Image Upload for Handwritten Answers
- Student photographs handwritten answer sheet
- Claude Vision reads handwriting and grades against rubric
- Confidence check prompt before grading
- Image preprocessing: contrast boost + B&W conversion
- **Why deferred:** typed answers are reliable; vision adds complexity without changing core value

### B2 — Interactive Graph Submission (Desmos)
- Student draws answer graph on embedded Desmos canvas
- App extracts structured data via Desmos API
- Structured data passed to LLM for grading
- **Why deferred:** typed answers cover non-graph questions first

### B3 — Weak Point Identification
- Track which topics student scores below 60% on across sessions
- Surface personalized recommendations: "You've struggled with Numerical Sequences across 3 sessions"
- **Why deferred:** requires persistent student history across sessions — already have users table, add analytics layer post-MVP

### B4 — Second Subject
- Architecture is fully subject-agnostic
- Adding a second subject = re-running ingestion pipeline with new documents + new curriculum JSON
- Strong candidate: GS Physics (same track, similar exam structure)
- **Why deferred:** depth over breadth

### B5 — Lebanese Textbook Full Ingestion
- Ingest complete "Building Up Mathematics" textbook via CRDP app export
- Section-based chunking preserving examples intact
- Enables explanation feature to reference exact textbook terminology and worked examples
- **Why deferred:** textbook PDF quality unknown; past exams sufficient for MVP

### B6 — Socratic Mode
- Agent asks student questions to test understanding instead of explaining directly
- Real pedagogical technique
- **Why deferred:** requires careful conversation flow management

### B7 — CI/CD Pipeline
- GitHub Actions: Docker build + smoke test + container health check on every push
- **Why deferred:** solo project; add only if instructor explicitly requires it

### B8 — Exam Photo Upload (Question Paper)
- Student photographs real past exam paper
- Claude Vision ingests it as a new exam session
- **Why deferred:** adds upload/processing flow complexity

### B9 — Grading Rules Table
- Structured Postgres table of topic-specific and question-type-specific grading rules
- Retrieved by metadata filter at grading time — not cosine similarity
- Eliminates context dilution from injecting all rules every time
- **Why deferred:** requires manually writing 30-50 rules with tags; flat rules injected via system prompt sufficient for MVP

### B10 — Tracing & Observability
- Every LLM call, tool call, and RAG retrieval as a trace span
- **Why deferred:** not required for MVP demo; add when debugging production issues

### B11 — Golden Evals
- Hand-curated set of 20-25 Lebanese Math questions with expected outputs
- CI gate that fails on regression
- **Why deferred:** time investment; add after MVP is stable

---

*Last updated after planning session with Claude — Kayan Abdulbaki*
