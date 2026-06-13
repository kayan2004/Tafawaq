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

export type Language = "en" | "fr";
export type Branch = "general_science" | "life_science";

export interface UserDetails {
  language: Language;
  grade: number;
  branch: Branch | null;
}

export async function getUserDetails(token: string): Promise<UserDetails | null> {
  const res = await fetch("/auth/me/details", {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (res.status === 404) return null;
  if (!res.ok) throw new Error("Failed to fetch profile details");
  return res.json() as Promise<UserDetails>;
}

export async function saveUserDetails(token: string, details: UserDetails): Promise<UserDetails> {
  const res = await fetch("/auth/me/details", {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(details),
  });
  if (!res.ok) {
    let detail = "Failed to save profile";
    try {
      const e = await res.json();
      if (Array.isArray(e.detail)) detail = e.detail.map((d: { msg: string }) => d.msg).join(", ");
      else if (typeof e.detail === "string") detail = e.detail;
    } catch { /* ignore */ }
    throw new Error(detail);
  }
  return res.json() as Promise<UserDetails>;
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

export interface PartResult {
  score: number;
  max_score: number;
  feedback: string;
  correction: string;
}

export interface ExerciseResult {
  exercise_id: number;
  parts: Record<string, PartResult>;
  exercise_total: number;
  exercise_max: number;
}

export interface EvaluatorResult {
  exercises: ExerciseResult[];
  grand_total: number;
  grand_max: number;
}

export interface AnswerPart {
  part: string;
  answer: string;
  submitted_at: string;
}

export interface ExerciseAnswer {
  exercise_id: number;
  parts: AnswerPart[];
}

export interface GradingApiResult {
  session_id: string;
  evaluator_1: EvaluatorResult;
  evaluator_2: EvaluatorResult;
  discrepancy_flagged: boolean;
  discrepancy_details: string | null;
  average_total: number;
  exam_content: ExamContent;
  student_answers: ExerciseAnswer[];
}

export async function submitExamAnswers(
  token: string,
  sessionId: string,
  answers: ExerciseAnswer[],
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

export async function getExamResults(token: string, sessionId: string): Promise<GradingApiResult | null> {
  const res = await fetch(`/exams/${sessionId}/results`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) return null;
  return res.json() as Promise<GradingApiResult>;
}

export interface ExtractedAnswers {
  answers: Array<{
    exercise_id: number;
    parts: Array<{ part: string; answer: string }>;
  }>;
}

export async function extractAnswers(
  token: string,
  sessionId: string,
  file: File,
): Promise<ExtractedAnswers> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`/exams/${sessionId}/extract-answers`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: form,
  });
  if (!res.ok) {
    let detail = `Extraction failed (${res.status})`;
    try {
      const e = await res.json();
      if (typeof e.error === "string") detail = e.error;
      else if (typeof e.detail === "string") detail = e.detail;
    } catch { /* ignore */ }
    throw new Error(detail);
  }
  return res.json() as Promise<ExtractedAnswers>;
}

// ── Official exams ────────────────────────────────────────────────────────────

export interface OfficialExam {
  id: string;
  year: number;
  session_label: string;
  exam_content: ExamContent;
}

export async function getOfficialExams(token: string): Promise<OfficialExam[]> {
  const res = await fetch("/official-exams", {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) return [];
  const data = await res.json();
  return Array.isArray(data) ? data : [];
}

export async function getOfficialExamPdfUrl(token: string, examId: string): Promise<string> {
  const res = await fetch(`/official-exams/${examId}/pdf`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("PDF not available");
  const blob = await res.blob();
  return URL.createObjectURL(blob);
}

export async function takeOfficialExam(
  token: string,
  examId: string,
): Promise<{ session_id: string; exam_content: ExamContent }> {
  const res = await fetch(`/official-exams/${examId}/take`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    let detail = `Failed to start exam (${res.status})`;
    try { const e = await res.json(); if (typeof e.detail === "string") detail = e.detail; } catch { /* ignore */ }
    throw new Error(detail);
  }
  return res.json() as Promise<{ session_id: string; exam_content: ExamContent }>;
}

// ── Textbook ──────────────────────────────────────────────────────────────────

export interface TextbookPageMeta {
  page_number: number;
  chapter: string;
  section: string;
  page_type: string;
}

export interface TextbookPage extends TextbookPageMeta {
  content: string;
}

export async function getTextbookToc(token: string): Promise<TextbookPageMeta[]> {
  const res = await fetch("/textbook/pages", {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) return [];
  const data = await res.json();
  return Array.isArray(data) ? data : [];
}

export async function getTextbookPage(token: string, pageNumber: number): Promise<TextbookPage | null> {
  const res = await fetch(`/textbook/page/${pageNumber}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) return null;
  return res.json() as Promise<TextbookPage>;
}

/** Fetch a textbook PDF from the backend (MinIO-backed) and return a blob URL.
 *  Caller must call URL.revokeObjectURL() when done. */
export async function getTextbookPdfBlobUrl(token: string, filename: string): Promise<string> {
  const res = await fetch(`/textbook/pdf/${encodeURIComponent(filename)}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error(`PDF not available (${res.status})`);
  const blob = await res.blob();
  return URL.createObjectURL(blob);
}

/** Opens a POST /chat SSE stream. Caller owns the reader. */
export async function startChatStream(
  message: string,
  token: string,
  signal: AbortSignal,
  attachedSessionId?: string | null,
): Promise<ReadableStreamDefaultReader<Uint8Array>> {
  const body: Record<string, unknown> = { message };
  if (attachedSessionId) body.attached_session_id = attachedSessionId;
  const res = await fetch("/chat", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(body),
    signal,
  });
  if (!res.ok) {
    if (res.status === 401) throw new Error("SESSION_EXPIRED");
    throw new Error(`Chat request failed (${res.status})`);
  }
  return res.body!.getReader();
}

export async function clearChatHistory(token: string): Promise<void> {
  await fetch("/chat/clear", {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });
}

export interface ChatHistoryMessage {
  role: "user" | "assistant";
  content: string;
}

export async function getChatHistory(token: string): Promise<ChatHistoryMessage[]> {
  const res = await fetch("/chat/history", {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) return [];
  const data = await res.json();
  return Array.isArray(data) ? data : [];
}

/** POST /tts — synthesize spoken-English text, returns audio/mpeg blob. */
export async function requestTts(token: string, text: string): Promise<Blob> {
  const res = await fetch("/tts", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ text }),
  });
  if (!res.ok) throw new Error(`TTS request failed (${res.status})`);
  return res.blob();
}
