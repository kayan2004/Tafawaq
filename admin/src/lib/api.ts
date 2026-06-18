/* api.ts — token storage and backend fetch helpers for the admin panel. */

const TOKEN_KEY = "tfw-admin-token";

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

export interface Me {
  is_superuser: boolean;
  name: string | null;
  email: string;
}

export async function getMe(token: string): Promise<Me> {
  const res = await fetch("/auth/me", {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("Failed to fetch user profile");
  const data = await res.json();
  return {
    is_superuser: Boolean(data.is_superuser),
    name: (data.name as string | null) ?? null,
    email: data.email as string,
  };
}

function authHeaders(token: string): HeadersInit {
  return { Authorization: `Bearer ${token}` };
}

async function getJson<T>(token: string, path: string): Promise<T> {
  const res = await fetch(path, { headers: authHeaders(token) });
  if (!res.ok) throw new Error(`Request failed (${res.status}): ${path}`);
  return res.json() as Promise<T>;
}

// ── Overview ──────────────────────────────────────────────────────────────────

export interface Overview {
  total_users: number;
  onboarded_users: number;
  onboarding_rate: number;
  exams_generated: number;
  exams_submitted: number;
  chunks_by_source_type: Record<string, number>;
  topics_tracked: number;
  messages_total: number;
  messages_7d: number;
  past_exam_files_total: number;
  past_exam_files_ingested: number;
}

export function getOverview(token: string): Promise<Overview> {
  return getJson<Overview>(token, "/admin/overview");
}

// ── Past-exam ingestion ──────────────────────────────────────────────────────

export interface PastExamFile {
  filename: string;
  year: number | null;
  session: number | null;
  ingested: boolean;
  chunk_count: number;
  parse_error: boolean;
}

export async function listPastExamFiles(token: string): Promise<PastExamFile[]> {
  const data = await getJson<{ files: PastExamFile[] }>(token, "/admin/ingestion/past-exams");
  return data.files;
}

export interface IngestionEvent {
  event: "file_progress" | "file_failed" | "done";
  file?: string;
  stage?: "extract" | "chunk" | "tag" | "embed" | "parse" | "done";
  chunks?: number;
  pages?: number;
  error?: string;
}

/** Opens a POST .../trigger SSE stream. Caller owns the reader. */
export async function triggerPastExamIngestion(
  token: string,
  filenames: string[],
  signal: AbortSignal,
): Promise<ReadableStreamDefaultReader<Uint8Array>> {
  const res = await fetch("/admin/ingestion/past-exams/trigger", {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders(token) },
    body: JSON.stringify({ filenames }),
    signal,
  });
  if (!res.ok) {
    let detail = `Ingestion trigger failed (${res.status})`;
    try {
      const e = await res.json();
      if (typeof e.error === "string") detail = e.error;
    } catch { /* ignore */ }
    throw new Error(detail);
  }
  return res.body!.getReader();
}

// ── Textbook ingestion ──────────────────────────────────────────────────────

export interface TextbookChapter {
  chapter: string;
  page_count: number;
  min_page: number;
  max_page: number;
}

export async function listTextbookChapters(token: string): Promise<TextbookChapter[]> {
  const data = await getJson<{ chapters: TextbookChapter[] }>(token, "/admin/ingestion/textbook");
  return data.chapters;
}

export async function triggerTextbookIngestion(
  token: string,
  files: File[],
  signal: AbortSignal,
): Promise<ReadableStreamDefaultReader<Uint8Array>> {
  const form = new FormData();
  for (const f of files) form.append("files", f);
  const res = await fetch("/admin/ingestion/textbook/trigger", {
    method: "POST",
    headers: authHeaders(token),
    body: form,
    signal,
  });
  if (!res.ok) throw new Error(`Ingestion trigger failed (${res.status})`);
  return res.body!.getReader();
}

/** Parses one SSE chunk buffer into individual `data: {...}` JSON events. */
export function parseSseEvents(buffer: string): { events: IngestionEvent[]; rest: string } {
  const events: IngestionEvent[] = [];
  const parts = buffer.split("\n\n");
  const rest = parts.pop() ?? "";
  for (const part of parts) {
    const line = part.trim();
    if (!line.startsWith("data:")) continue;
    const payload = line.slice(5).trim();
    if (payload === "[DONE]") continue;
    try {
      events.push(JSON.parse(payload) as IngestionEvent);
    } catch { /* ignore malformed chunk */ }
  }
  return { events, rest };
}

// ── Topics ────────────────────────────────────────────────────────────────────

export interface TopicStat {
  topic: string;
  appearances: number;
  last_seen_year: number;
  last_seen_session: number;
  frequency_tier: "high" | "medium" | "low";
}

export interface TopicsResponse {
  topics: TopicStat[];
  gaps: string[];
}

export function getTopics(token: string): Promise<TopicsResponse> {
  return getJson<TopicsResponse>(token, "/admin/topics");
}

// ── Guardrails ──────────────────────────────────────────────────────────────

export interface GuardrailsSummary {
  messages_7d: number;
  blocked: number;
  warned: number;
  block_rate: number;
}

export function getGuardrailsSummary(token: string): Promise<GuardrailsSummary> {
  return getJson<GuardrailsSummary>(token, "/admin/guardrails/summary");
}

export interface GuardrailMessage {
  ts: string;
  text: string;
  score: number;
  level: "blocked" | "warned";
  reason: string;
}

export async function getGuardrailsMessages(token: string): Promise<GuardrailMessage[]> {
  const data = await getJson<{ messages: GuardrailMessage[] }>(token, "/admin/guardrails/messages");
  return data.messages;
}

// ── Users ───────────────────────────────────────────────────────────────────

export interface AdminUser {
  id: string;
  email: string;
  is_active: boolean;
  created_at: string;
  last_login: string | null;
  onboarded: boolean;
  exam_count: number;
  avg_score: number | null;
}

export async function listUsers(token: string): Promise<AdminUser[]> {
  const data = await getJson<{ users: AdminUser[] }>(token, "/admin/users");
  return data.users;
}

export async function deactivateUser(token: string, userId: string): Promise<void> {
  const res = await fetch(`/admin/users/${userId}/deactivate`, {
    method: "POST",
    headers: authHeaders(token),
  });
  if (!res.ok) throw new Error(`Failed to deactivate user (${res.status})`);
}
