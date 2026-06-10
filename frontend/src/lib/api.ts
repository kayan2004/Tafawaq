/* api.ts — token storage and backend fetch helpers. */

const TOKEN_KEY = "math_coach_token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

export async function login(email: string, password: string): Promise<string> {
  const body = new URLSearchParams({ username: email, password });
  const res = await fetch("/auth/jwt/login", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: body.toString(),
  });
  if (!res.ok) {
    let detail = "Login failed";
    try {
      const err = await res.json();
      if (typeof err.detail === "string") detail = err.detail;
    } catch { /* ignore */ }
    throw new Error(detail);
  }
  const data = await res.json();
  return data.access_token as string;
}

export async function register(email: string, password: string): Promise<void> {
  const res = await fetch("/auth/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    let detail = "Registration failed";
    try {
      const err = await res.json();
      if (typeof err.detail === "string") detail = err.detail;
      else if (Array.isArray(err.detail))
        detail = err.detail.map((d: { msg: string }) => d.msg).join(", ");
    } catch { /* ignore */ }
    throw new Error(detail);
  }
}

export async function getMe(token: string): Promise<{ is_superuser: boolean }> {
  const res = await fetch("/auth/me", {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("Failed to fetch user profile");
  const data = await res.json();
  return { is_superuser: data.is_superuser as boolean };
}

// ── Exam types ────────────────────────────────────────────────────────────────

export interface ExamPart {
  part: string;
  marks: number;
  content: string;
}

export interface ExamExercise {
  id: number;
  topic: string;
  total_marks: number;
  content: string;
  parts: ExamPart[];
}

export interface ExamContent {
  exercises: ExamExercise[];
}

export interface ActiveExamSession {
  session_id: string;
  status: string;
  exam_content: ExamContent;
}

export async function getActiveSession(token: string): Promise<ActiveExamSession | null> {
  const res = await fetch("/exams/active", {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (res.status === 404) return null;
  if (!res.ok) return null;
  return res.json() as Promise<ActiveExamSession>;
}

export interface ExamSessionSummary {
  session_id: string;
  session_type: string;
  status: string;
  created_at: string;
}

export async function getExamHistory(token: string): Promise<ExamSessionSummary[]> {
  const res = await fetch("/exams/sessions", {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) return [];
  const data = await res.json();
  return Array.isArray(data) ? data : [];
}

export async function getExamSession(token: string, sessionId: string): Promise<ActiveExamSession | null> {
  const res = await fetch(`/exams/${sessionId}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) return null;
  return res.json() as Promise<ActiveExamSession>;
}

/** Opens a POST /exams/generate SSE stream. Caller owns the reader. */
export async function generateExamStream(
  token: string,
  signal: AbortSignal,
): Promise<ReadableStreamDefaultReader<Uint8Array>> {
  const res = await fetch("/exams/generate", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ session_type: "mock_generated" }),
    signal,
  });
  if (!res.ok) {
    if (res.status === 409) throw new Error("ACTIVE_SESSION_EXISTS");
    throw new Error(`Exam generation failed (${res.status})`);
  }
  return res.body!.getReader();
}

export interface GradingApiResult {
  session_id: string;
  evaluator_1: { exercises: unknown[]; grand_total: number; grand_max: number };
  evaluator_2: { exercises: unknown[]; grand_total: number; grand_max: number };
  discrepancy_flagged: boolean;
  discrepancy_details: string | null;
  average_total: number;
}

export async function submitExamAnswers(
  token: string,
  sessionId: string,
  answers: Array<{ exercise_id: number; parts: Array<{ part: string; answer: string; submitted_at: string }> }>,
): Promise<GradingApiResult> {
  const res = await fetch("/grade", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ session_id: sessionId, answers }),
  });
  if (!res.ok) {
    let detail = `Submission failed (${res.status})`;
    try { const e = await res.json(); if (typeof e.detail === "string") detail = e.detail; } catch { /* ignore */ }
    throw new Error(detail);
  }
  return res.json() as Promise<GradingApiResult>;
}

/** Opens a POST /chat SSE stream. Caller owns the reader. */
export async function startChatStream(
  message: string,
  conversationId: string | null,
  token: string,
  signal: AbortSignal,
): Promise<ReadableStreamDefaultReader<Uint8Array>> {
  const res = await fetch("/chat", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({
      message,
      ...(conversationId ? { conversation_id: conversationId } : {}),
    }),
    signal,
  });
  if (!res.ok) {
    if (res.status === 401) throw new Error("SESSION_EXPIRED");
    throw new Error(`Chat request failed (${res.status})`);
  }
  return res.body!.getReader();
}
