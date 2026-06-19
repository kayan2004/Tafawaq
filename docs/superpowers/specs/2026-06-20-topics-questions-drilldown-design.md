# Topics → Questions drill-down — design

## Context

`frontend/src/pages/Topics.tsx` already renders a frequency-analytics list
of curriculum topics (`GET /topics/stats`) — one row per topic with a tier
chip, appearance count, and a frequency bar. Rows are currently inert; there
is no way to see the actual past-exam questions behind a topic's count.

The backend already fully supports this: `GET /topics/{topic}/questions`
(`app/api/routers/topics.py` → `topic_service.get_questions_by_topic`)
returns a list of `PastQuestion` records (`chunk_id`, `year`, `session`,
`exercise_id`, `topic`, `question_type`, `marks`, `content`, `answer`) for
a given topic, with optional `year_from`/`year_to`/`question_type`/`limit`
query params. Nothing in the frontend calls it yet.

This is a frontend-only feature: wire the existing endpoint to a new
drill-down view inside `Topics.tsx`.

## Scope

**In scope:**
- A `getQuestionsByTopic(token, topic)` client in `frontend/src/lib/api.ts`.
- Clicking a topic row in `Topics.tsx` switches the page into a drill-down
  view listing that topic's past questions as boxes, with a back control
  to return to the topic list.
- Each question box: header badges (year, session label, question type,
  marks) + question content rendered via `RichMath` (existing KaTeX/markdown
  renderer) + a per-box "Show answer" toggle that reveals the answer key
  (also via `RichMath`) on demand.
- Loading / error / empty states for the drill-down view, consistent with
  the existing list view's `page-hint` pattern.

**Out of scope (deferred, not forgotten):**
- Filter controls (year range, question type) in the drill-down view —
  the backend already accepts `year_from`/`year_to`/`question_type`, so
  this is a pure additive follow-up with no backend work needed.
- Pagination beyond the backend's default `limit=50` — acceptable for v1
  given current data volumes (Math GS exams, ~20 PDFs ingested).
- URL/hash deep-linking into a specific topic's question view — the page
  uses local component state only, mirroring how `Exam.tsx` already
  switches between its own internal "browse" / "detail" phases without
  touching `window.location.hash`.
- Any backend changes — the endpoint, service, and repo layer are already
  complete and unmodified by this work.

## Architecture / data flow

```
Topics.tsx (list view)
  → user clicks a topic row
  → setSelectedTopic(topic) triggers a view switch (local state, no routing)
  → drill-down view mounts, calls getQuestionsByTopic(token, topic)
  → GET /topics/{topic}/questions (existing, unmodified)
  → renders PastQuestion[] as boxes
  → "← Back to Topics" clears selectedTopic, returns to list view
```

No new `PageId`, no new route, no new backend endpoint. The whole feature
lives inside the existing `Topics` component plus one new function in
`lib/api.ts`.

## Components

**`frontend/src/lib/api.ts`** — add:
```ts
export interface PastQuestion {
  chunk_id: string;
  year: number;
  session: number;
  exercise_id: number;
  topic: string;
  question_type: string;
  marks: number;
  content: string;
  answer: string | null;
}

export async function getQuestionsByTopic(token: string, topic: string): Promise<PastQuestion[]> {
  const res = await fetch(`/topics/${encodeURIComponent(topic)}/questions`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) return [];
  const data = await res.json();
  return Array.isArray(data.questions) ? (data.questions as PastQuestion[]) : [];
}
```
`topic` is URL-encoded since topic names contain spaces/slashes (e.g.
"Natural Logarithm / Exponential Function").

**`frontend/src/pages/Topics.tsx`** — add local state:
- `selectedTopic: string | null` on the top-level `Topics` component —
  drives list view vs. drill-down view (when set, render the drill-down
  block instead of the topics list).
- A new local, non-exported `TopicQuestions({ topic, onBack })` function
  component in the same file (mirroring how `ExerciseList` is a local
  function inside `Exam.tsx`, not a separate module). It owns its own
  `questions` / `loading` / `error` state, fetches via
  `getQuestionsByTopic` in a `useEffect` keyed on `topic`, and tracks
  per-card answer visibility with a `Set<string>` of revealed `chunk_id`s.
- Each topic row gets `onClick={() => setSelectedTopic(t.topic)}` plus a
  hover/cursor affordance (`cursor: pointer` already implied by making it
  a `<button>`-like clickable row, consistent with other clickable rows
  in this codebase).

**Styling** — reuse `.exam-exercise` / `.exam-exercise-header` /
`.exam-exercise-stem` box pattern from `frontend/src/styles/pages.css`
(already used for rendering question content + parts in `Exam.tsx`) rather
than introducing a parallel set of "question box" classes. Add a small
`.topic-q-answer-toggle` / `.topic-q-answer` pair of classes for the
show/hide answer affordance, following existing naming conventions in
`pages.css`.

## Error handling

- Fetch failure → `error` state → reuse `page-hint` text, same as the
  existing topic list's `"Failed to load topic data."` pattern.
- Empty result (topic exists but has zero questions, or unmapped) →
  `page-hint` empty-state message.
- `answer` is nullable on `PastQuestion` (the Pydantic field default) —
  if null, the "Show answer" control is omitted entirely for that box
  rather than revealing nothing.

## Testing / verification plan

- Manual verification via the running dev stack: load Topics page, click
  a topic with known appearances, confirm questions render with correct
  LaTeX/markdown rendering, confirm "Show answer" toggle works per-box
  independently, confirm "Back to Topics" returns to the frequency list
  with state intact (no refetch needed, list state untouched).
- No backend changes — no backend test changes required.
- No automated frontend test suite currently exists for `Topics.tsx`
  (confirmed by checking the existing test setup); manual verification in
  the browser is the verification method for this pass, consistent with
  how `Exam.tsx`/`Dashboard.tsx` UI work has been verified previously in
  this project.
