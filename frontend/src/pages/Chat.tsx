/* Chat.tsx — streaming chat with the Lebanese GS Math AI coach. */
import { useEffect, useRef, useState } from "react";
import { Icons } from "../lib/icons";
import { RichMath } from "../lib/math";
import {
  clearToken,
  getChatHistory,
  getChatSessions,
  createChatSession,
  renameChatSession,
  getExamHistory,
  getToken,
  requestTts,
  startChatStream,
} from "../lib/api";
import type { ChatSession, ExamSessionSummary } from "../lib/api";
import { SessionPicker } from "../components/SessionPicker";
import { messageToSpeech } from "../lib/speechify";
// @ts-ignore — JSX component, no type declarations
import TafawwaqMascot from "../../TafawwaqMascot";
import { SlashCommandPicker } from "../components/SlashCommandPicker";
import type { SlashCommandPickerHandle, SlashSendPayload } from "../components/SlashCommandPicker";

interface RetrieveMatch {
  year: number;
  session: number;
  marks: number;
  content: string;
  why: string;
}

interface Msg {
  id: number;
  role: "user" | "assistant" | "tool";
  content: string;
  streaming: boolean;
  toolName?: string;
  toolInput?: Record<string, unknown>;
  noTools?: boolean;
  kind?: "retrieve";
}

interface Props {
  onLogout: () => void;
  isAdmin?: boolean;
  onCommand?: (cmd: string) => void;
  isDark?: boolean;
}

let _seq = 0;
const nextId = () => ++_seq;

// Matches scores ≥ 14/20 in any assistant message
const NAILED_RE = /\b(1[4-9]|20)\s*\/\s*20\b/;

export function Chat({ onLogout, isAdmin = false, onCommand, isDark = true }: Props) {
  // Session management
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSession, setActiveSession] = useState<ChatSession | null>(null);

  const [messages, setMessages] = useState<Msg[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [playingId, setPlayingId] = useState<number | null>(null);
  const [loadingId, setLoadingId] = useState<number | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  // Mascot state
  const [isNailed, setIsNailed] = useState(false);
  const [mouthOpen, setMouthOpen] = useState(false);
  const nailedResetRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const rafRef = useRef<number | null>(null);

  // Derived mascot state — priority: nailed > talking > thinking > idle
  const mascotState: "idle" | "thinking" | "talking" | "nailed" =
    isNailed ? "nailed" :
    playingId !== null ? "talking" :
    isStreaming ? "thinking" :
    "idle";

  const fireNailed = () => {
    if (nailedResetRef.current) clearTimeout(nailedResetRef.current);
    setIsNailed(true);
    nailedResetRef.current = setTimeout(() => setIsNailed(false), 1800);
  };

  // Attached exam state
  const [attachedSession, setAttachedSession] = useState<ExamSessionSummary | null>(null);
  const [pickerOpen, setPickerOpen] = useState(false);
  const [pickerSessions, setPickerSessions] = useState<ExamSessionSummary[]>([]);
  const [pickerSearch, setPickerSearch] = useState("");
  const [pickerLoading, setPickerLoading] = useState(false);
  const pickerRef = useRef<HTMLDivElement>(null);
  const pickerSearchRef = useRef<HTMLInputElement>(null);

  const [activeCmd, setActiveCmd] = useState<string | null>(null);
  const slashPickerRef = useRef<SlashCommandPickerHandle>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);
  const imageInputRef = useRef<HTMLInputElement>(null);

  // Image attachment for /retrieve
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imageBase64, setImageBase64] = useState<string | null>(null);
  const [imageMimeType, setImageMimeType] = useState<string | null>(null);
  const [imagePreviewUrl, setImagePreviewUrl] = useState<string | null>(null);

  useEffect(() => {
    if (!imageFile) { setImagePreviewUrl(null); return; }
    const url = URL.createObjectURL(imageFile);
    setImagePreviewUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [imageFile]);

  const clearImage = () => {
    setImageFile(null);
    setImageBase64(null);
    setImageMimeType(null);
  };

  const onImageSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setImageFile(file);
    setImageMimeType(file.type);
    const reader = new FileReader();
    reader.onload = () => {
      const result = reader.result as string;
      setImageBase64(result.split(",")[1]);
    };
    reader.readAsDataURL(file);
    e.target.value = "";
  };

  // Cancel rAF on unmount
  useEffect(() => {
    return () => {
      if (rafRef.current !== null) cancelAnimationFrame(rafRef.current);
      if (nailedResetRef.current !== null) clearTimeout(nailedResetRef.current);
    };
  }, []);

  // Load sessions on mount; auto-create a default if none exist
  useEffect(() => {
    const token = getToken();
    if (!token) return;
    getChatSessions(token).then(async (fetched) => {
      if (fetched.length === 0) {
        const created = await createChatSession(token, "math_gs12");
        setSessions([created]);
        setActiveSession(created);
      } else {
        setSessions(fetched);
        setActiveSession(fetched[0]);
      }
    });
  }, []);

  // Load history whenever the active session changes
  useEffect(() => {
    if (!activeSession) return;
    const token = getToken();
    if (!token) return;
    setMessages([]);
    getChatHistory(token, activeSession.id).then((history) => {
      if (history.length === 0) return;
      setMessages(
        history.map((m) => {
          const base: Msg = { id: nextId(), role: m.role, content: m.content, streaming: false };
          if (m.role === "assistant") {
            try {
              const parsed = JSON.parse(m.content);
              if (parsed?.event === "retrieve_result") return { ...base, kind: "retrieve" as const };
            } catch { /* not JSON */ }
          }
          return base;
        })
      );
    });
  }, [activeSession?.id]);

  const handleSessionSelect = (s: ChatSession) => {
    if (s.id === activeSession?.id) return;
    setActiveSession(s);
  };

  const handleSessionCreate = async (subject: string, title?: string) => {
    const token = getToken();
    if (!token) return;
    const created = await createChatSession(token, subject, title);
    setSessions((prev) => [created, ...prev]);
    setActiveSession(created);
  };

  const handleSessionRename = async (sessionId: string, title: string) => {
    const token = getToken();
    if (!token) return;
    const updated = await renameChatSession(token, sessionId, title);
    setSessions((prev) => prev.map((s) => (s.id === sessionId ? updated : s)));
    if (activeSession?.id === sessionId) setActiveSession(updated);
  };

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

  const send = async (payload: SlashSendPayload) => {
    const text = payload.text.trim();
    if (!text || isStreaming) return;

    const token = getToken();
    if (!token) { onLogout(); return; }

    // Slash-command dispatch — /retrieve falls through to the chat API; others are handled here
    if (text.startsWith("/")) {
      const cmd = text.slice(1).split(/\s+/)[0].toLowerCase();
      if (cmd === "generate") {
        setMessages((prev) => [
          ...prev,
          { id: nextId(), role: "user", content: text, streaming: false },
          { id: nextId(), role: "assistant", content: "Sure! I've queued a new mock exam for you — head to the Exams tab whenever you're ready.", streaming: false },
        ]);
        onCommand?.("generate");
        return;
      } else if (cmd === "exam") {
        openPicker();
        return;
      } else if (cmd === "retrieve") {
        const query = text.slice("/retrieve".length).trim();
        if (!query && !imageFile) {
          setMessages((prev) => [
            ...prev,
            { id: nextId(), role: "user", content: text, streaming: false },
            { id: nextId(), role: "assistant", content: "Usage: `/retrieve <question>` — or attach an image of a problem to find similar past exam questions.", streaming: false },
          ]);
          return;
        }
        // /retrieve with a query or image falls through to the streaming path below
      } else {
        setMessages((prev) => [
          ...prev,
          { id: nextId(), role: "user", content: text, streaming: false },
          { id: nextId(), role: "assistant", content: `Unknown command: \`/${cmd}\``, streaming: false },
        ]);
        return;
      }
    }

    setIsStreaming(true);

    const initialAsstId = nextId();
    // Mutable ref so appendToken/finishMsg always target the latest assistant bubble,
    // even after tool-call interleaving creates new ones.
    const asstIdRef = { current: initialAsstId };
    let accumulated = "";

    setMessages((prev) => [
      ...prev,
      { id: nextId(), role: "user", content: text, streaming: false },
      { id: initialAsstId, role: "assistant", content: "", streaming: true },
    ]);

    const abort = new AbortController();
    abortRef.current = abort;
    let pendingToolId: number | null = null;

    const appendToken = (chunk: string) => {
      accumulated += chunk;
      setMessages((prev) => {
        const last = prev[prev.length - 1];
        if (!last || last.id !== asstIdRef.current) return prev;
        return [...prev.slice(0, -1), { ...last, content: last.content + chunk }];
      });
    };

    const finishMsg = (override?: string) =>
      setMessages((prev) => {
        const last = prev[prev.length - 1];
        if (!last || last.id !== asstIdRef.current) return prev;
        return [
          ...prev.slice(0, -1),
          { ...last, streaming: false, content: override !== undefined ? override : last.content },
        ];
      });

    // Close current assistant bubble, insert a pending tool chip, open a fresh assistant bubble.
    const splitForTool = () => {
      const oldAsstId = asstIdRef.current;
      const toolId = nextId();
      const newAsstId = nextId();
      pendingToolId = toolId;
      asstIdRef.current = newAsstId;
      setMessages((prev) => [
        ...prev.map((m) => (m.id === oldAsstId ? { ...m, streaming: false } : m)),
        { id: toolId, role: "tool" as const, content: "…", streaming: false },
        { id: newAsstId, role: "assistant" as const, content: "", streaming: true },
      ]);
    };

    const resolveToolLabel = (label: string) => {
      if (pendingToolId === null) return;
      const id = pendingToolId;
      pendingToolId = null;
      setMessages((prev) => prev.map((m) => (m.id === id ? { ...m, content: label } : m)));
    };

    if (!activeSession) return;

    try {
      const reader = await startChatStream(text, token, abort.signal, activeSession.id, attachedSession?.session_id, imageBase64 ?? null, imageMimeType ?? null);
      clearImage();
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
          } else if (event === "retrieve_result") {
            const resultJson = JSON.stringify({ event: "retrieve_result", matches: payload.matches });
            setMessages((prev) => {
              const last = prev[prev.length - 1];
              if (!last || last.id !== asstIdRef.current) return prev;
              return [...prev.slice(0, -1), { ...last, content: resultJson, streaming: false, kind: "retrieve" as const }];
            });
            done = true;
            break;
          } else if (event === "tool_use") {
            splitForTool();
          } else if (event === "textbook_page") {
            const pn = payload.page_number as number;
            const sec = payload.section as string | undefined;
            resolveToolLabel(sec ? `Retrieved textbook page ${pn} — ${sec}` : `Retrieved textbook page ${pn}`);
          } else if (event === "textbook_sections") {
            const secs = payload.sections as unknown[];
            resolveToolLabel(`Retrieved ${secs.length} relevant textbook section${secs.length !== 1 ? "s" : ""}`);
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

      finishMsg();

      // Fire nailed if the response contains a score ≥ 14/20
      if (NAILED_RE.test(accumulated)) fireNailed();
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

  const stopRaf = () => {
    if (rafRef.current !== null) {
      cancelAnimationFrame(rafRef.current);
      rafRef.current = null;
    }
    setMouthOpen(false);
  };

  const handleSpeak = async (msg: Msg) => {
    // Stop any in-progress amplitude loop first
    stopRaf();

    if (playingId === msg.id) {
      audioRef.current?.pause();
      audioRef.current = null;
      setPlayingId(null);
      return;
    }
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
      setPlayingId(null);
    }
    if (loadingId !== null) return;

    const token = getToken();
    if (!token) return;

    setLoadingId(msg.id);
    try {
      const blob = await requestTts(token, messageToSpeech(msg.content));
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      audioRef.current = audio;
      setPlayingId(msg.id);

      // AudioContext must be created on a user gesture — the click is the gesture.
      if (!audioCtxRef.current) {
        audioCtxRef.current = new AudioContext();
      }
      const ctx = audioCtxRef.current;
      if (ctx.state === "suspended") await ctx.resume();

      const source = ctx.createMediaElementSource(audio);
      const analyser = ctx.createAnalyser();
      analyser.fftSize = 256;
      source.connect(analyser);
      analyser.connect(ctx.destination);
      analyserRef.current = analyser;

      // rAF loop: read frequency amplitude → drive mouthOpen
      const data = new Uint8Array(analyser.frequencyBinCount);
      const tick = () => {
        analyser.getByteFrequencyData(data);
        const loudness = data.reduce((a, b) => a + b, 0) / data.length;
        setMouthOpen(loudness > 28);
        rafRef.current = requestAnimationFrame(tick);
      };
      rafRef.current = requestAnimationFrame(tick);

      audio.addEventListener("ended", () => {
        URL.revokeObjectURL(url);
        stopRaf();
        setPlayingId(null);
        if (audioRef.current === audio) audioRef.current = null;
      });

      audio.play();
    } catch {
      // silently fail — TTS is best-effort
    } finally {
      setLoadingId(null);
    }
  };

  const SpeakerIcon = Icons.speaker;
  const ImageIcon = Icons.image;

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
        <div className="chat-mascot-header">
          <SessionPicker
            sessions={sessions}
            activeSession={activeSession}
            onSelect={handleSessionSelect}
            onCreate={handleSessionCreate}
            onRename={handleSessionRename}
            disabled={isStreaming}
          />
        </div>
      </div>

      {/* ── Messages ── */}
      <div className="chat-messages">
        {messages.length === 0 && (
          <div className="chat-empty">
            <TafawwaqMascot
              state={mascotState}
              mouthOpen={mouthOpen}
              isDark={isDark}
              size={120}
            />
            <p className="chat-empty-line1">مرحبا — I'm Noor, your Tafawwaq tutor.</p>
            <p className="chat-empty-line2">What are we working on?</p>
          </div>
        )}

        {messages.map((msg) => {
          if (msg.role === "tool") {
            const BookIcon = Icons.book;
            return (
              <div key={msg.id} className="msg-tool">
                <BookIcon size={14} className="" />
                {msg.content}
              </div>
            );
          }

          // Skip empty non-streaming assistant bubbles (can appear before tool chips)
          if (msg.role === "assistant" && !msg.streaming && !msg.content) return null;

          // Retrieve-result cards
          if (msg.role === "assistant" && msg.kind === "retrieve") {
            let matches: RetrieveMatch[] = [];
            try {
              const parsed = JSON.parse(msg.content);
              if (Array.isArray(parsed.matches)) matches = parsed.matches;
            } catch { /* empty */ }
            return (
              <div key={msg.id} className="msg msg-ai">
                <div className="chat-retrieve-cards">
                    {matches.length === 0 ? (
                      <p className="chat-retrieve-empty">No similar past exam questions found.</p>
                    ) : (
                      matches.map((m, i) => (
                        <div key={i} className="chat-retrieve-card">
                          <div className="chat-retrieve-card-header">
                            <span className="chat-retrieve-year">{m.year}</span>
                            <span className="chat-retrieve-dot">·</span>
                            <span className="chat-retrieve-session">Session {m.session}</span>
                            <span className="chat-retrieve-dot">·</span>
                            <span className="chat-retrieve-marks">{m.marks} marks</span>
                          </div>
                          <div className="chat-retrieve-latex">
                            <RichMath streaming={false}>{m.content}</RichMath>
                          </div>
                          <p className="chat-retrieve-why">{m.why}</p>
                        </div>
                      ))
                    )}
                  </div>
              </div>
            );
          }

          return (
            <div key={msg.id} className={`msg ${msg.role === "assistant" ? "msg-ai" : "msg-user"}`}>
              {msg.role === "assistant" ? (
                <RichMath streaming={msg.streaming}>{msg.content}</RichMath>
              ) : (
                msg.content
              )}
              {msg.role === "assistant" && !msg.streaming && msg.content && (
                <div className="chat-content-actions">
                  <button
                    className={`chat-speak-btn${playingId === msg.id ? " is-playing" : ""}${loadingId === msg.id ? " is-loading" : ""}`}
                    onClick={() => handleSpeak(msg)}
                    disabled={loadingId !== null}
                    aria-label={playingId === msg.id ? "Stop reading" : "Read aloud"}
                  >
                    {loadingId === msg.id ? (
                      <span className="chat-speak-spinner" />
                    ) : (
                      <SpeakerIcon size={14} className="" />
                    )}
                  </button>
                </div>
              )}
            </div>
          );
        })}

        <div ref={bottomRef} />
      </div>

      {/* ── Corner mascot (visible while conversation is running) ── */}
      {messages.length > 0 && (
        <div className="chat-mascot-corner">
          <TafawwaqMascot
            state={mascotState}
            mouthOpen={mouthOpen}
            isDark={isDark}
            size={64}
          />
        </div>
      )}

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

      {/* ── Image preview chip ── */}
      {imageFile && imagePreviewUrl && (
        <div className="chat-image-chip-bar">
          <div className="chat-image-chip">
            <img className="chat-image-thumb" src={imagePreviewUrl} alt="" />
            <span className="chat-image-chip-name">{imageFile.name}</span>
            <button className="chat-image-chip-dismiss" onClick={clearImage} aria-label="Remove image">×</button>
          </div>
        </div>
      )}

      {/* ── Input bar ── */}
      <div className="chat-input-bar">
        <input
          ref={imageInputRef}
          type="file"
          accept="image/jpeg,image/png,image/webp,image/gif"
          style={{ display: "none" }}
          onChange={onImageSelect}
        />
        <SlashCommandPicker
          ref={slashPickerRef}
          onSelect={(cmd) => { if (cmd === "/exam") openPicker(); }}
          onSend={send}
          disabled={isStreaming}
          onChipChange={setActiveCmd}
          adornment={
            activeCmd === "/retrieve" ? (
              <button
                type="button"
                className={`chat-image-attach-btn${imageFile ? " has-image" : ""}`}
                onClick={() => imageInputRef.current?.click()}
                disabled={isStreaming}
                title="Attach an image of the problem"
                aria-label="Attach image"
              >
                <ImageIcon size={18} className="" />
              </button>
            ) : undefined
          }
        />
      </div>

    </div>
  );
}
