/* Chat.tsx — streaming chat with the Lebanese GS Math AI coach. */
import { useEffect, useRef, useState } from "react";
import { Icons } from "../lib/icons";
import { RichMath } from "../lib/math";
import {
  clearChatHistory,
  clearToken,
  getChatHistory,
  getExamHistory,
  getToken,
  startChatStream,
} from "../lib/api";
import type { ExamSessionSummary } from "../lib/api";

interface Msg {
  id: number;
  role: "user" | "assistant" | "tool";
  content: string;
  streaming: boolean;
  toolName?: string;
  toolInput?: Record<string, unknown>;
  noTools?: boolean;
}

interface Props {
  onLogout: () => void;
  isAdmin?: boolean;
  onCommand?: (cmd: string) => void;
}

let _seq = 0;
const nextId = () => ++_seq;

export function Chat({ onLogout, isAdmin = false, onCommand }: Props) {
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);

  // Attached exam state
  const [attachedSession, setAttachedSession] = useState<ExamSessionSummary | null>(null);
  const [pickerOpen, setPickerOpen] = useState(false);
  const [pickerSessions, setPickerSessions] = useState<ExamSessionSummary[]>([]);
  const [pickerSearch, setPickerSearch] = useState("");
  const [pickerLoading, setPickerLoading] = useState(false);
  const pickerRef = useRef<HTMLDivElement>(null);
  const pickerSearchRef = useRef<HTMLInputElement>(null);

  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  // Load persisted history on first mount
  useEffect(() => {
    const token = getToken();
    if (!token) return;
    getChatHistory(token).then((history) => {
      if (history.length === 0) return;
      setMessages(
        history.map((m) => ({ id: nextId(), role: m.role, content: m.content, streaming: false }))
      );
    });
  }, []);

  // Close picker on outside click
  useEffect(() => {
    if (!pickerOpen) return;
    const handler = (e: MouseEvent) => {
      if (pickerRef.current && !pickerRef.current.contains(e.target as Node)) {
        setPickerOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [pickerOpen]);

  // Focus search when picker opens
  useEffect(() => {
    if (pickerOpen) setTimeout(() => pickerSearchRef.current?.focus(), 0);
  }, [pickerOpen]);

  const openPicker = async () => {
    const token = getToken();
    if (!token) return;
    setPickerOpen(true);
    setPickerSearch("");
    setPickerLoading(true);
    const sessions = await getExamHistory(token);
    setPickerSessions(sessions);
    setPickerLoading(false);
  };

  // Auto-scroll to bottom whenever messages update
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Auto-grow the textarea
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  }, [input]);

  const send = async () => {
    const text = input.trim();
    if (!text || isStreaming) return;

    const token = getToken();
    if (!token) { onLogout(); return; }

    setInput("");

    // Slash-command dispatch — never reaches the chat API
    if (text.startsWith("/")) {
      const cmd = text.slice(1).split(/\s+/)[0].toLowerCase();
      if (cmd === "generate") {
        setMessages((prev) => [
          ...prev,
          { id: nextId(), role: "user", content: text, streaming: false },
          { id: nextId(), role: "assistant", content: "Sure! I've queued a new mock exam for you — head to the Exams tab whenever you're ready.", streaming: false },
        ]);
        onCommand?.("generate");
      } else if (cmd === "exam") {
        setInput("");
        openPicker();
      } else {
        setMessages((prev) => [
          ...prev,
          { id: nextId(), role: "user", content: text, streaming: false },
          { id: nextId(), role: "assistant", content: `Unknown command: \`/${cmd}\``, streaming: false },
        ]);
      }
      return;
    }

    setIsStreaming(true);

    const initialAsstId = nextId();
    // Mutable ref so appendToken/finishMsg always target the latest assistant bubble,
    // even after tool-call interleaving creates new ones.
    const asstIdRef = { current: initialAsstId };

    setMessages((prev) => [
      ...prev,
      { id: nextId(), role: "user", content: text, streaming: false },
      { id: initialAsstId, role: "assistant", content: "", streaming: true },
    ]);

    const abort = new AbortController();
    abortRef.current = abort;
    let toolCalled = false;

    const appendToken = (chunk: string) =>
      setMessages((prev) => {
        const last = prev[prev.length - 1];
        if (!last || last.id !== asstIdRef.current) return prev;
        return [...prev.slice(0, -1), { ...last, content: last.content + chunk }];
      });

    const finishMsg = (override?: string) =>
      setMessages((prev) => {
        const last = prev[prev.length - 1];
        if (!last || last.id !== asstIdRef.current) return prev;
        return [
          ...prev.slice(0, -1),
          { ...last, streaming: false, content: override !== undefined ? override : last.content },
        ];
      });

    // Close current assistant bubble, insert a tool chip, open a fresh assistant bubble.
    const addToolAndContinue = (toolName: string, toolInput: Record<string, unknown>) => {
      const oldAsstId = asstIdRef.current;
      const toolId = nextId();
      const newAsstId = nextId();
      asstIdRef.current = newAsstId;
      setMessages((prev) => [
        ...prev.map((m) => (m.id === oldAsstId ? { ...m, streaming: false } : m)),
        { id: toolId, role: "tool" as const, content: "", streaming: false, toolName, toolInput },
        { id: newAsstId, role: "assistant" as const, content: "", streaming: true },
      ]);
    };

    try {
      const reader = await startChatStream(text, token, abort.signal, attachedSession?.session_id);
      const decoder = new TextDecoder();
      let buffer = "";
      let done = false;

      while (!done) {
        const { done: streamDone, value } = await reader.read();
        if (streamDone) break;

        buffer += decoder.decode(value, { stream: true });

        // SSE frames are separated by double-newline
        const frames = buffer.split("\n\n");
        buffer = frames.pop() ?? "";

        for (const frame of frames) {
          const line = frame.trim();
          if (!line.startsWith("data: ")) continue;
          const raw = line.slice(6);
          if (raw === "[DONE]") { done = true; break; }

          let payload: Record<string, unknown>;
          try { payload = JSON.parse(raw); } catch { continue; }

          const event = payload.event as string;
          if (event === "token") {
            appendToken(payload.text as string);
          } else if (event === "tool_use" && isAdmin) {
            toolCalled = true;
            addToolAndContinue(
              payload.name as string,
              payload.input as Record<string, unknown>,
            );
          } else if (event === "guardrail_block") {
            finishMsg(payload.message as string);
            done = true;
            break;
          } else if (event === "guardrail_warning") {
            appendToken("\n\n" + (payload.message as string));
          } else if (event === "done") {
            done = true;
            break;
          }
        }
      }

      if (isAdmin && !toolCalled) {
        const noToolId = nextId();
        const currentAsstId = asstIdRef.current;
        setMessages((prev) => {
          const idx = prev.findIndex((m) => m.id === currentAsstId);
          if (idx === -1) return prev;
          const indicator: Msg = { id: noToolId, role: "tool", content: "", streaming: false, noTools: true };
          return [...prev.slice(0, idx), indicator, ...prev.slice(idx)];
        });
      }
      finishMsg();
    } catch (err) {
      const name = (err as Error).name;
      const msg = (err as Error).message;
      if (name === "AbortError") {
        finishMsg();
      } else if (msg === "SESSION_EXPIRED") {
        clearToken();
        onLogout();
        return;
      } else {
        finishMsg(msg || "Something went wrong. Please try again.");
      }
    } finally {
      setIsStreaming(false);
      abortRef.current = null;
    }
  };

  const onKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  const newChat = () => {
    abortRef.current?.abort();
    setMessages([]);
    setIsStreaming(false);
    const token = getToken();
    if (token) clearChatHistory(token).catch(() => {});
    setTimeout(() => textareaRef.current?.focus(), 0);
  };

  const handleLogout = () => {
    abortRef.current?.abort();
    clearToken();
    onLogout();
  };

  const SendIcon = Icons.send;

  const filteredSessions = pickerSessions.filter((s) => {
    if (!pickerSearch) return true;
    const q = pickerSearch.toLowerCase();
    return (
      s.session_type.toLowerCase().includes(q) ||
      s.status.toLowerCase().includes(q) ||
      new Date(s.created_at).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" }).toLowerCase().includes(q)
    );
  });

  function sessionLabel(s: ExamSessionSummary): string {
    const type = s.session_type === "mock_generated" ? "Mock" : s.session_type === "official" ? "Official" : s.session_type;
    const date = new Date(s.created_at).toLocaleDateString("en-GB", { day: "numeric", month: "short" });
    return `${type} · ${date}`;
  }

  return (
    <div className="chat-wrap">
      {/* ── Header ── */}
      <div className="chat-header">
        <div>
          <div className="chat-header-title">AI Math Coach</div>
          <div className="chat-header-sub">
            Lebanese GS Grade 12 · Curriculum-scoped
            {isAdmin && <span className="chat-admin-badge">admin</span>}
          </div>
        </div>
        <div className="chat-header-actions">
          <button
            className="btn btn-ghost"
            style={{ fontSize: 13, padding: "7px 14px" }}
            onClick={newChat}
          >
            New chat
          </button>
          <button
            className="link-btn"
            style={{ fontSize: 13, color: "var(--muted)" }}
            onClick={handleLogout}
          >
            Sign out
          </button>
        </div>
      </div>

      {/* ── Messages ── */}
      <div className="chat-messages">
        {messages.length === 0 && (
          <div className="chat-empty">
            <div className="chat-empty-mark">∑</div>
            <p className="chat-empty-title">Ask the Math Coach anything</p>
            <p className="chat-empty-hint">
              Functions · Integrals · Probability · Complex numbers · Space geometry
            </p>
            <div className="chat-suggestions">
              {[
                "Explain how to find the center of symmetry of a rational function",
                "Walk me through integration by parts with an example",
                "What are the main theorems I need for complex numbers?",
              ].map((s) => (
                <button
                  key={s}
                  type="button"
                  className="chat-suggestion"
                  onClick={() => { setInput(s); textareaRef.current?.focus(); }}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg) => {
          if (msg.role === "tool") {
            const SparkIcon = Icons.spark;
            if (msg.noTools) {
              return (
                <div key={msg.id} className="chat-tool-call chat-tool-none">
                  <SparkIcon size={14} className="chat-tool-icon" />
                  <span className="chat-tool-none-label">no tools were used</span>
                </div>
              );
            }
            return (
              <div key={msg.id} className="chat-tool-call">
                <SparkIcon size={14} className="chat-tool-icon" />
                <div className="chat-tool-body">
                  <span className="chat-tool-name">{msg.toolName}</span>
                  <pre className="chat-tool-input">
                    {JSON.stringify(msg.toolInput, null, 2)}
                  </pre>
                </div>
              </div>
            );
          }

          // Skip empty non-streaming assistant bubbles (can appear before tool chips)
          if (msg.role === "assistant" && !msg.streaming && !msg.content) return null;

          return (
            <div key={msg.id} className={`chat-bubble ${msg.role}`}>
              <div className={`chat-avatar ${msg.role}`}>
                {msg.role === "assistant" ? "∑" : "You"}
              </div>
              <div className="chat-content">
                {msg.role === "assistant" ? (
                  <RichMath streaming={msg.streaming}>{msg.content}</RichMath>
                ) : (
                  msg.content
                )}
              </div>
            </div>
          );
        })}

        <div ref={bottomRef} />
      </div>

      {/* ── Exam picker ── */}
      {pickerOpen && (
        <div className="chat-exam-picker" ref={pickerRef}>
          <input
            ref={pickerSearchRef}
            className="chat-exam-picker-search"
            placeholder="Search by type, date, or status…"
            value={pickerSearch}
            onChange={(e) => setPickerSearch(e.target.value)}
            onKeyDown={(e) => e.key === "Escape" && setPickerOpen(false)}
          />
          <div className="chat-exam-picker-list">
            {pickerLoading && <div className="chat-exam-picker-empty">Loading…</div>}
            {!pickerLoading && filteredSessions.length === 0 && (
              <div className="chat-exam-picker-empty">No exams found</div>
            )}
            {!pickerLoading && filteredSessions.map((s) => (
              <button
                key={s.session_id}
                className={`chat-exam-picker-item${attachedSession?.session_id === s.session_id ? " selected" : ""}`}
                onClick={() => { setAttachedSession(s); setPickerOpen(false); }}
              >
                <span className={`chat-exam-type-badge ${s.session_type}`}>
                  {s.session_type === "mock_generated" ? "Mock" : "Official"}
                </span>
                <span className="chat-exam-picker-date">
                  {new Date(s.created_at).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" })}
                </span>
                <span className={`chat-exam-status ${s.status}`}>{s.status}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* ── Attached exam chip ── */}
      {attachedSession && !pickerOpen && (
        <div className="chat-exam-chip-bar">
          <div className="chat-exam-chip">
            <span className="chat-exam-chip-label">📎 {sessionLabel(attachedSession)}</span>
            <button
              className="chat-exam-chip-dismiss"
              onClick={() => setAttachedSession(null)}
              aria-label="Remove attached exam"
            >×</button>
          </div>
        </div>
      )}

      {/* ── Input bar ── */}
      <div className="chat-input-bar">
        <textarea
          ref={textareaRef}
          className="chat-input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder="Ask about derivatives, probability, complex numbers… (Enter to send, Shift+Enter for new line)"
          rows={1}
          disabled={isStreaming}
        />
        <button
          type="button"
          className="btn btn-blue chat-send-btn"
          onClick={send}
          disabled={isStreaming || !input.trim()}
          aria-label="Send message"
        >
          <SendIcon size={18} className="" />
        </button>
      </div>
    </div>
  );
}
