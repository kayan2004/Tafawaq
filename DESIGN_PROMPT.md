# Design Prompt — Lebanese Math Coach

## What to design

A complete, production-quality UI/UX redesign for **Lebanese Math Coach** — a web application that helps Lebanese Grade 12 (GS) students prepare for the official Mathematics Baccalaureate exam. Design every screen described below. The app is fully built on the backend; only the visual design needs work.

---

## Target user

Lebanese GS Grade 12 student, age 17–18, studying intensively for the Baccalaureate. Uses the app daily on both laptop and phone. Needs to feel focused, confident, and supported — not overwhelmed. The exam is high-stakes (it determines university admission).

---

## Design language

- **Warm-educational**: soft blues and greens, nothing clinical or corporate
- **Friendly but serious**: rounded cards and smooth transitions, but not childish
- **Math-first**: content must breathe — LaTeX equations, multi-line problem statements, and long answers need generous whitespace
- **Current token values to preserve or improve upon**:
  - Primary blue: `#3b82d9`, deep blue: `#2a64b5`
  - Green (success/submit): `#1aa37a`
  - Background: `#eef3f9` (soft cool-white)
  - Surface (cards): `#ffffff`
  - Ink: `#1d2a3a`, secondary ink: `#46566b`
  - Danger/high-frequency: coral `#e5604d`
  - Amber/medium-frequency: `#e89a2c`
  - Border radius: `10–20px` range, pill buttons at `999px`
  - Font: Inter

---

## App shell

**Fixed left sidebar (248px wide)** on desktop, **bottom tab bar** on mobile (≤860px).

Sidebar contains:
- Brand mark: gradient square logo (blue→green), app name "Lebanese Math Coach", subtitle "GS Grade 12"
- Navigation items (icon + label): Dashboard, Practice Exam, Chat, History, Topics
- Bottom: user avatar card (initials avatar, email, logout button)

Active nav item uses a soft blue tint background with blue text.

---

## Pages to design

### 1. Login / Register

Two states on the same screen — toggle between Login and Register.

**Login fields**: Email, Password, "Sign in" button  
**Register fields**: Email, Password, "Create account" button  
Toggle link at bottom: "Don't have an account? Register" / "Already have an account? Sign in"

Show validation errors inline (e.g. "Invalid credentials", "Email already registered").  
Clean centered card layout, brand mark at top.

---

### 2. Dashboard (home)

The student's command center. Shows at a glance: how they're doing, what to do next, upcoming exam countdown.

**Hero CTA card** (full-width, two-column):
- Left: "Recommended next" label, headline "Sit a full 3-hour mock", subtext about AI grading, two buttons: **Start Practice Exam** (green, primary) and **Ask the coach** (ghost)
- Right: Score ring — circular progress showing last score range (e.g. "14–16 / 20") with animated fill

**4 stat tiles** in a grid:
- Mocks completed (count)
- Study streak (days, flame icon)
- Average score / 20
- Questions practised

**Two-column lower section**:
- **Focus topics panel**: top 4 topics by exam frequency, each row shows topic name, frequency bar, frequency badge colored by tier (coral = high, amber = medium, green = low)
- **Recent attempts panel**: last 3 exam sessions, each row shows title, date, score range badge

---

### 3. Practice Exam page

One page, multiple sub-states:

#### 3a. Browse state

Two sections stacked vertically:

**Official Exams section**  
Grid or list of 19 official Lebanese GS Baccalaureate exams (2004–2024). Each card shows:
- Year (large) + session label (e.g. "Session 1", "Exceptional")
- Total marks badge (e.g. "20 pts") + "Official" green badge
- "View" button

**Generated Mock Exams section**  
List of the student's AI-generated mock exams. Each row shows:
- Date and time created
- Status badge: "In Progress" (grey) / "Submitted" (blue) / "Graded" (green)
- "Mathematics" pill
- "Continue" (if in progress) or "View" button

Button to generate a new mock exam (triggers streaming generation).

#### 3b. Official exam detail state (after clicking "View")

Full-page layout:
- Header: back button, title "Mathematics — 2021 Exceptional", subtitle "Lebanese GS Official Baccalaureate Exam", mark badge, "Official" badge, **Start Exam** button
- Main card: **Embedded PDF iframe** (75vh height) showing the official exam document for preview. Skeleton shimmer while PDF loads. "PDF could not be loaded" fallback text.

#### 3c. Mock exam detail state (after clicking "View" on a generated exam)

Full-page layout:
- Header: back button, title "Mathematics — Mock Exam", date/time, mark badge, status badge, **Start Exam** (if in progress), **Export PDF** button
- Main card: Full exam content rendered with LaTeX — exercise headers, stems, parts with marks

#### 3d. Exam generation in progress

Streaming SSE from backend. Show a loading state with animated indicator while the exam generates (takes ~15–20 seconds). The session_id arrives first via SSE, then the full exam content.

#### 3e. Exam taking state (modal-like, full viewport)

**Top bar** (fixed, full-width):
- Left: exercise tab buttons — I, II, III, IV, V (or more). Active tab highlighted blue. Completed tab shows a checkmark or dot.
- Right: **Desmos** button (opens graphing calculator panel), **View PDF** button (only for official exams — opens PDF in new tab, disabled until PDF blob loads), **Submit (X/Y)** blue button showing answered/total exercise count

**Body** (scrollable):
- Exercise header: "Exercise II — Complex Numbers" + mark total
- Exercise preamble text (LaTeX rendered)
- Sub-questions listed vertically. Each sub-question:
  - Part label + marks (e.g. "1) 2 pts" or "3a) 0.5 pts")
  - Question text with LaTeX
  - Answer textarea: "Write your solution here…" placeholder, auto-grows
- Navigation footer: ← Previous Exercise | 2 / 5 | Next Exercise →

**Desmos side panel** (slides in from right when Desmos button clicked):
- Panel header with "Desmos Graphing Calculator" title and close button
- Full Desmos embedded graphing calculator
- "Use Graph →" button at bottom — inserts a LaTeX expression reference into the focused answer textarea

**Submit confirmation**: `window.confirm` dialog, then "Grading…" loading state on the submit button.

#### 3f. Grading result state

Appears after submission is graded (takes ~30–60 seconds, two parallel AI evaluators).

Three-column score display:
- Strict evaluator score (e.g. 13.5 / 20)
- **Average score** (center, larger, e.g. 14.0 / 20) — this is the headline result
- Lenient evaluator score (e.g. 14.5 / 20)

Discrepancy warning (amber banner) if the two evaluators disagreed significantly.

"Back to exams" button.

---

### 4. Chat page

AI math tutor — streaming conversation interface.

Layout: full-height chat UI with message list + input bar.

**Message bubbles**:
- User messages: right-aligned, blue background
- Assistant messages: left-aligned, white card, full LaTeX rendering
- Tool-use messages (when AI retrieves textbook content): subtle grey row, shows which tool was called (e.g. "Retrieved textbook page 14")
- Streaming: blinking cursor at end of in-progress assistant message

**Input bar** (fixed bottom):
- Auto-growing textarea (max ~5 lines)
- Send button (icon, active when text is present)
- Disabled with "Responding…" state while streaming

**Guardrail states**:
- Warning (2nd off-topic message): amber inline notice appended to assistant message — "Warning: this is your 2nd off-topic question. One more and further off-topic messages will be blocked."
- Blocked (3rd+ off-topic): red inline banner, message not shown

Empty state (no messages yet): centered welcome message — "Ask anything about the Lebanese GS Math curriculum."

---

### 5. History page

List of all the student's exam sessions (mock-generated only — official exam sessions are in the Exams page).

**List view**: chronological list of exam session rows, same card style as in the Exam browse page.

**Detail view** (after clicking a session):
- Back button
- Exam title + date header
- Status badge + Export PDF button
- Full read-only exam content rendered with LaTeX (exercises, parts, question text)
- If graded: show the grading result (scores from both evaluators + average)

Empty state: "No exams generated yet. Head to the Practice Exam tab."

---

### 6. Topics page (stub — design the intended UI)

Analytics on which topics appear most often in past Lebanese GS exams (derived from the official exam corpus).

**Topic frequency list**: each row shows:
- Topic name (e.g. "Functions and Curve Study", "Complex Numbers", "Probability")
- Frequency bar — colored by tier:
  - Coral: appears 8–10 times (high priority)
  - Amber: appears 4–7 times (medium priority)
  - Green: appears 1–3 times (low priority)
- Count badge (e.g. "9/10")
- Tier label chip

Header stats: total topics tracked, last updated year.

"Focus on high-frequency topics" guidance callout at top.

---

## Component catalogue (reuse across pages)

| Component | Description |
|---|---|
| **Pill / Badge** | Rounded label: `blue`, `green`, `amber`, `coral`, `grey` variants |
| **Card** | White surface, `14–20px` radius, subtle border + shadow |
| **Skeleton shimmer** | Animated gradient placeholder during loading |
| **Status badge** | In Progress (grey), Submitted (blue), Graded (green) |
| **Tier chip** | Small colored dot — coral / amber / green for topic frequency |
| **Exercise tab** | Compact button labeled I–VI, active state + answered indicator |
| **Answer textarea** | Full-width, auto-grow, monospace-adjacent font for math input |
| **Score ring** | Circular progress gauge for score display |
| **Frequency bar** | Horizontal fill bar, color-coded by tier |

---

## Key UX constraints

1. **LaTeX rendering everywhere** — exercise content, chat messages, and history views all contain inline and display-mode LaTeX (rendered with KaTeX). The design must accommodate mixed text+math, multi-line equations, and display-block formulas without overflow.

2. **Streaming states** — exam generation (~20s) and chat responses stream token-by-token via SSE. Show clear in-progress states; don't show empty content areas.

3. **Exam taking is full-screen** — when a student is taking an exam, the experience should feel focused and distraction-free. The top taking-bar stays fixed; the body scrolls.

4. **Mobile**: sidebar collapses to a 5-tab bottom bar. Chat, exam taking, and dashboard all need to work well on a 390px-wide screen.

5. **PDF embed**: the official exam detail view embeds the real PDF in an iframe. Design must accommodate a tall iframe (75vh) cleanly within the card.

6. **Desmos panel**: the graphing calculator slides in as a side panel during exam taking. On desktop it pushes the body content left; on mobile it overlays.

---

## What NOT to design

- Admin panel (not in scope)
- Results page (not yet built — skip)
- Notifications or email flows
- Any onboarding / tutorial flow
- Pricing or settings pages
