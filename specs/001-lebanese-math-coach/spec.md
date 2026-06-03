# Feature Specification: Lebanese Math Coach

**Feature Branch**: `001-lebanese-math-coach`

**Created**: 2026-06-03

**Status**: Draft

**Input**: User description: "Build a Lebanese GS Grade 12 Mathematics exam preparation platform
called Lebanese Math Coach for Lebanese high school students studying for the official Lebanese
Baccalaureate exam."

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Mock Exam Generation (Priority: P1)

A student opens the platform and requests a full practice exam. The system generates a complete
mock exam that matches the structure of the official Lebanese GS Math baccalaureate exam: 20 total
points, obligatory questions covering the same topic areas as recent official exams, formatted with
proper math notation and any required graphs. The student can begin answering immediately.

**Why this priority**: Without a realistic mock exam, the platform has no central experience to
build around. This is the starting point for every other feature.

**Independent Test**: A student can request, receive, and read a complete mock exam without
submitting answers or accessing any other feature. The exam renders correctly with math notation
and graphs visible.

**Acceptance Scenarios**:

1. **Given** a logged-in student on the exam generation screen, **When** they request a mock exam,
   **Then** a complete 20-point exam is displayed with all questions obligatory, math notation
   rendered, and any graphs visible — within 30 seconds.
2. **Given** a generated exam, **When** the student reviews it, **Then** every question includes
   a topic label, marks allocation per sub-part, and a clear question number.
3. **Given** a generated exam, **When** the student attempts to access a topic excluded from
   the current year's curriculum, **Then** that topic does not appear in the generated exam.

---

### User Story 2 — Answer Submission and Dual Evaluation (Priority: P1)

A student completes a mock exam (or a real past exam) and submits their written answers. The
platform sends the submission to two independent AI evaluators simultaneously. Each evaluator
grades the answers against the exam's answer key. One evaluator applies strict grading (deducts
on doubt), the other applies lenient grading (awards on doubt), mirroring how two independent
Lebanese correctors would grade the same paper. Both results are displayed side by side. Where
the evaluators assign different scores, a clear visual indicator flags the discrepancy so the
student knows which parts of their answer are borderline.

**Why this priority**: Grading is the core value proposition — students need actionable feedback
tied to the real Lebanese grading system. Without this, the mock exam has no payoff.

**Independent Test**: A student submits typed answers for a mock exam and receives two scored
evaluations displayed side by side with discrepancies highlighted, without needing to use any
other feature.

**Acceptance Scenarios**:

1. **Given** a student who has answered all questions in a session, **When** they submit the exam,
   **Then** two evaluations appear side by side — each showing a score per sub-question, a total
   score out of 20, written feedback, and a list of missing keywords — within 60 seconds.
2. **Given** two evaluations for the same submission, **When** the evaluators assign different
   scores to a sub-question, **Then** that sub-question is visually flagged as a discrepancy and
   the difference in scores is displayed.
3. **Given** two evaluations with no discrepancies, **When** the student views the results,
   **Then** no discrepancy flag appears and both total scores match.
4. **Given** a submission for a real past official exam, **When** evaluation is complete, **Then**
   the grading is performed against the official answer key for that exam year and session.
5. **Given** a submission for a generated mock exam, **When** evaluation is complete, **Then**
   the grading is performed against the answer key that was generated alongside the exam.

---

### User Story 3 — Past Question Retrieval (Priority: P2)

A student wants to drill a specific topic. They ask the platform to retrieve past official exam
questions on that topic, optionally filtering by year range and question type. The platform returns
a ranked list of matching questions from the official exam archive (2000–2026), each showing the
year, session, marks, question text, and official answer. The student can use this to practice
targeted material in the style Lebanese examiners actually write.

**Why this priority**: Targeted practice with real past questions is the second-most-valuable use
case after mock exams. It requires only retrieval, not grading, making it independently deliverable.

**Independent Test**: A student queries for all integration questions from 2015–2024 and receives
a list of matching past exam questions with official answers, without needing to start an exam
session.

**Acceptance Scenarios**:

1. **Given** a student who enters a topic and optional year range, **When** they submit the query,
   **Then** a list of matching past exam questions is returned within 5 seconds, each showing
   year, session, marks, question text, and official answer.
2. **Given** a natural-language query (e.g., "give me probability questions from the last 5 years"),
   **When** the student submits it, **Then** the system interprets the intent and returns relevant
   results without requiring the student to use exact topic names.
3. **Given** a query with no matching results, **When** the student submits it, **Then** a
   clear "no results found" message is displayed with a suggestion to broaden the search.

---

### User Story 4 — Topic Frequency Analytics (Priority: P2)

A student wants to know which topics to prioritize before the exam. They open the analytics
dashboard and see all GS Math topics ranked by how often they have appeared across the 26 years
of past exams. Each topic shows a color-coded frequency indicator (high / medium / low) and the
last year it appeared. Clicking a topic reveals all past exam questions on that topic.

**Why this priority**: Knowing topic frequency helps students allocate study time rationally. This
feature requires no AI at display time, making it fast and independently demonstrable.

**Independent Test**: A student opens the topic analytics dashboard and sees all topics ranked with
color coding and last-seen years, then clicks one topic and sees its past questions — without
starting an exam session or chatting with the AI.

**Acceptance Scenarios**:

1. **Given** a student on the analytics dashboard, **When** it loads, **Then** all GS Math topics
   are displayed ranked by appearance frequency across past exams, with a color indicator
   (red = high frequency ≥ 7 of 10 recent years, yellow = medium, green = low) and a "last seen"
   year — within 3 seconds.
2. **Given** the analytics dashboard, **When** a student clicks a topic, **Then** all past exam
   questions on that topic are displayed, filterable by year.
3. **Given** the analytics dashboard, **When** the student views it before any exam session,
   **Then** it is fully accessible as a standalone study tool.

---

### User Story 5 — Topic Explanation Grounded in Lebanese Exam Style (Priority: P2)

A student doesn't understand a topic and asks the AI coach to explain it. Rather than giving a
generic textbook explanation, the platform explains the topic specifically in terms of how Lebanese
examiners test it — what types of questions appear, how solutions are expected to be structured,
and what common student mistakes cost marks. The explanation is followed by 2–3 real past exam
questions on the topic as practice examples. The student also sees how frequently this topic
appears across past exams.

**Why this priority**: Exam-grounded explanations are the platform's differentiator from general
tutoring tools. This is independently valuable without requiring a full exam session.

**Independent Test**: A student asks "explain integration by parts" and receives an explanation
that references how Lebanese examiners test this, includes 2–3 real past questions as examples,
and states how often the topic appears — without starting an exam session.

**Acceptance Scenarios**:

1. **Given** a student who asks about a topic, **When** the AI responds, **Then** the explanation
   references the Lebanese exam context (question types, common mark-deduction points) rather
   than being a generic definition.
2. **Given** a topic explanation response, **When** the student reads it, **Then** 2–3 real past
   exam questions on that topic are included as examples, each with the official answer.
3. **Given** a topic explanation, **When** it is displayed, **Then** a frequency note is included
   (e.g., "This topic appeared in 8 of the last 10 exams").
4. **Given** a student asking about an out-of-scope topic, **When** the AI responds, **Then**
   it clearly states the topic is not in the current year's curriculum and suggests in-scope
   alternatives.

---

### User Story 6 — Curriculum Scope Awareness (Priority: P3)

A student asks about a mathematical topic. Before answering, the platform checks whether the
topic is in the current year's official Lebanese GS Math curriculum. If it is not, the platform
informs the student clearly rather than explaining a topic they will not be tested on. This ensures
the student's study time is spent only on examinable material.

**Why this priority**: Curriculum scoping prevents wasted study time. It is a cross-cutting
concern that enhances other features (exam generation, explanations) but can be validated
independently.

**Independent Test**: A student asks about a topic that was removed from the current year's
curriculum (e.g., oblique asymptotes). The platform responds that this topic is out of scope
for the current year and does not provide an explanation.

**Acceptance Scenarios**:

1. **Given** a student asking about an in-scope topic, **When** the AI responds, **Then** no
   out-of-scope warning appears and the explanation proceeds normally.
2. **Given** a student asking about a topic removed from the current year's curriculum, **When**
   the AI responds, **Then** the response states the topic is not examinable this year and
   names in-scope alternatives if any exist.
3. **Given** a curriculum update for a new academic year, **When** the curriculum is updated
   by the platform operator (no code change required), **Then** all subsequent AI responses
   and exam generation respect the new scope automatically.

---

### User Story 7 — Off-Topic Guardrails (Priority: P3)

A student starts sending messages unrelated to Lebanese GS Math exam preparation (e.g., asking
about other subjects, or requesting general homework help). The platform detects off-topic
messages and gently redirects the student. After repeated off-topic messages in a session, the
platform soft-blocks further off-topic responses with a clear redirect message, keeping the
tool focused on its purpose.

**Why this priority**: Guardrails protect the platform from scope creep and ensure it remains
a focused exam preparation tool. This is independently testable and does not depend on any other
user story being complete.

**Independent Test**: A student sends multiple off-topic messages. After the second consecutive
off-topic message, a redirect reminder appears. After a third, a soft-block message is shown.
When the student returns to an exam-related question, normal responses resume.

**Acceptance Scenarios**:

1. **Given** a student sending a clearly on-topic message, **When** the AI responds, **Then**
   no redirect reminder appears and the response is fully on topic.
2. **Given** a student who has sent 2 consecutive off-topic messages, **When** they send
   another message, **Then** the response includes a gentle redirect reminder alongside the reply.
3. **Given** a student who has sent 3 or more consecutive off-topic messages, **When** they
   send another off-topic message, **Then** the system responds with a soft-block message
   redirecting them to exam preparation topics, without answering the off-topic request.
4. **Given** a student who was soft-blocked, **When** they send an on-topic exam question,
   **Then** normal responses resume and the off-topic counter resets.

---

### Edge Cases

- What happens when a student submits an exam session after it has expired (3-hour TTL)?
- How does the system handle a math question that has no matching past exam questions in the archive?
- What if both evaluators return the exact same total score but different per-question scores?
- What if a student submits completely blank answers?
- What if the student asks about a topic that exists in past exams but is not in the current year's curriculum?
- What happens if the AI generates an exam containing a question type not seen in recent years?
- What happens when a student tries to start a new exam session while one is already in progress?
- What happens if the AI service is unreachable during exam generation, evaluation, or explanation?

---

## Clarifications

### Session 2026-06-03

- Q: Can a student have multiple active exam sessions simultaneously? → A: No — one active session at a time; creating a new exam is blocked while an in-progress session exists.
- Q: Are evaluation results saved after a session ends? → A: Yes — results are permanently saved and accessible in a student history view after the session expires or is graded.
- Q: What should happen if the AI service is unavailable when a student tries to generate an exam or submit answers? → A: Display a clear error message ("Service temporarily unavailable") with a retry button; no request is silently lost.
- Q: Should students be able to export or share their evaluation results? → A: No — results are visible in-app only; export/sharing is deferred to post-MVP.
- Q: Can a student retake a previously generated mock exam? → A: No — every new session always generates a fresh exam; retaking the same generated exam is not supported.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST generate complete mock exams matching the official Lebanese GS Math
  baccalaureate structure (20 points total, obligatory questions, topic coverage consistent with
  recent official exams).
- **FR-002**: System MUST render math notation and graphs clearly within the exam interface so
  students can read questions without ambiguity.
- **FR-003**: Students MUST be able to submit typed answers per question or as a complete exam
  in a single submission.
- **FR-004**: System MUST evaluate submitted answers using two independent AI graders operating
  with distinct philosophies: one strict (deducts on doubt) and one lenient (awards on doubt).
- **FR-005**: Each evaluator MUST return: a score per sub-question, a total score out of 20,
  written feedback, and a list of missing answer keywords.
- **FR-006**: System MUST visually flag every sub-question where the two evaluators assign
  different scores, and display the score difference.
- **FR-007**: For real past official exam submissions, grading MUST be performed against the
  official answer key for the specified exam year and session.
- **FR-008**: For generated mock exam submissions, grading MUST be performed against the answer
  key that was generated alongside the exam at session creation time.
- **FR-009**: System MUST allow students to retrieve past official exam questions filtered by
  topic, question type, and year range.
- **FR-010**: Past question results MUST include: year, session, marks, question text, and
  official answer.
- **FR-011**: System MUST support natural-language retrieval queries (students need not use exact
  topic names).
- **FR-012**: System MUST display all GS Math topics ranked by frequency of appearance across
  past official exams.
- **FR-013**: Topic frequency display MUST include: color-coded frequency tier (high/medium/low),
  appearance count, and last-seen year.
- **FR-014**: Clicking a topic in the frequency dashboard MUST display all past exam questions
  tagged with that topic.
- **FR-015**: System MUST provide AI-generated topic explanations framed around how Lebanese
  examiners test the topic, not generic textbook definitions.
- **FR-016**: Topic explanations MUST include 2–3 real past exam questions as worked examples
  and state the topic's frequency across past exams.
- **FR-017**: System MUST enforce the current year's curriculum: topics marked as out-of-scope
  MUST NOT appear in generated exams and MUST trigger an out-of-scope notice when asked about.
- **FR-018**: Curriculum scope MUST be updatable by the platform operator without code changes
  (via a configuration file).
- **FR-019**: System MUST detect off-topic messages and apply a three-tier response:
  on-topic (normal response), drifting (include gentle redirect reminder), off-topic (soft-block
  with redirect message).
- **FR-020**: Off-topic session state MUST reset when the student returns to exam-relevant queries.
- **FR-021**: Exam sessions MUST expire after 3 hours; expired sessions MUST NOT accept new
  answer submissions.
- **FR-022**: System MUST require student authentication (registration and login) to access
  exam sessions and grading history.
- **FR-023**: All AI responses (exam generation, evaluation, explanation) MUST stream to the
  student interface progressively, not appear all at once after a delay.
- **FR-024**: A student MUST NOT be able to start a new exam session while an existing session
  is in-progress (status = in_progress). The system MUST block new session creation and inform
  the student that they have an active session, until that session is submitted or expires.
- **FR-025**: Evaluation results (both evaluators' scores, feedback, and discrepancy flags) MUST
  be permanently saved per student and accessible in a personal history view after the session
  ends, with no expiry.
- **FR-026**: When any AI-dependent operation fails (exam generation, evaluation, topic
  explanation), the system MUST display a clear error message ("Service temporarily unavailable")
  and present a retry option. No request MUST fail silently.

### Key Entities

- **Student**: A registered user preparing for the Lebanese GS Math baccalaureate exam.
  Attributes: email, registration date, last login.
- **Exam Session**: A bounded practice event containing a full exam. Has a session type
  (generated mock or real past exam), exam content, answer key, status
  (in progress / submitted / graded), and an expiry time. A student may have at most one
  in-progress session at any time; a new session cannot be created until the current one
  is submitted or expires.
- **Past Exam Question**: A question extracted from an official Lebanese GS Math past exam.
  Tagged with: topic, subtopic, year, session number, question type (proof / calculation / MCQ /
  sketch), and marks.
- **Answer Key**: The official or generated solution set for an exam. For past exams, derived
  from official answer key documents. For mock exams, generated by the AI at session creation.
- **Evaluation Report**: The grading output from one AI evaluator. Contains per-sub-question
  scores, total score, written feedback, and missing keywords. Two reports exist per submission.
- **Topic**: A subject area in the Lebanese GS Math curriculum. Has a frequency count and
  last-seen year derived from the past exam archive. Marked as in-scope or out-of-scope for
  the current academic year.
- **Conversation Turn**: A single student message and its AI response within a chat session.
  Carries an off-topic classification score used for guardrail logic.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Students can generate a complete mock exam in under 30 seconds from clicking
  "Generate Exam."
- **SC-002**: Dual evaluation results for a complete exam submission are displayed within
  60 seconds of submission.
- **SC-003**: Topic frequency analytics dashboard loads in under 3 seconds and requires no
  AI processing at display time.
- **SC-004**: Past question retrieval returns results for any valid topic/year query in under
  5 seconds.
- **SC-005**: 100% of queries about out-of-curriculum topics result in an explicit out-of-scope
  message — no out-of-scope topic is silently explained as if it were in scope.
- **SC-006**: Students can identify all evaluator discrepancies by scanning the results page
  once — no manual score comparison is needed.
- **SC-007**: Off-topic redirection triggers within the same response turn — no off-topic
  message is silently processed without a redirect signal after the second consecutive
  off-topic message.
- **SC-008**: Exam sessions remain accessible for the full 3-hour exam duration without
  requiring the student to re-authenticate or re-generate.
- **SC-009**: Curriculum scope updates take effect for all students immediately after the
  operator updates the curriculum file — no platform restart or code deployment required.

---

## Assumptions

- Students type their answers in plain text; formatted mathematical notation input is not
  required from the student side (the AI interprets plain-text math expressions).
- The platform supports the **English-track** Lebanese GS Math exam only; the French-track exam
  is out of scope for the initial version.
- The 75 past official English-track exams (2000–2026) with answer keys have been legally
  obtained from Apelr and are available for ingestion before the platform launches.
- The curriculum JSON defining in-scope and out-of-scope topics for the current academic year
  (2024–2025) is manually created and maintained by the platform operator (Kayan Abdulbaki);
  this is not automated.
- The platform is a web application used from desktop browsers; mobile browser optimization
  is a post-MVP concern.
- Student registration and login are required; anonymous sessions are not supported in the
  initial version.
- Handwritten answer upload (photo of answer sheet) is out of scope for the initial version.
- Interactive graph sketching by the student (e.g., drawing a curve on a canvas) is out of
  scope for the initial version; graphs appear only in questions, not in answer submission.
- The platform ingests text content from PDFs only; diagram images within past exam PDFs are
  skipped in the initial version.
- Two AI evaluators running in parallel is sufficient for dual-grading; no human review step
  is included in the initial version.
- Evaluation result export (PDF download, shareable links) is out of scope for the initial
  version; results are accessible in-app only.
- Each generated mock exam is always fresh — retaking a previously generated exam is not
  supported in the initial version.
