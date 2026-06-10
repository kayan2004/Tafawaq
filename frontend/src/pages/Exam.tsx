import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import { getToken, getActiveSession, generateExamStream, submitExamAnswers, ExamExercise } from "../lib/api";
import { RichMath } from "../lib/math";
import { Pill } from "../lib/ui";

// Desmos JS API types (subset we use)
interface DesmosExpression { id: string; latex?: string; hidden?: boolean; }
interface DesmosCalculator { getExpressions(): DesmosExpression[]; destroy(): void; }
declare global {
  interface Window {
    Desmos?: { GraphingCalculator(el: HTMLElement, opts?: Record<string, unknown>): DesmosCalculator; };
  }
}

const ROMAN = ["I", "II", "III", "IV", "V", "VI"];

// ── Phase type ────────────────────────────────────────────────────────────────

type Phase =
  | { kind: "loading" }
  | { kind: "setup" }
  | { kind: "generating" }
  | { kind: "exam"; exercises: ExamExercise[]; sessionId: string }
  | { kind: "taking"; exercises: ExamExercise[]; sessionId: string }
  | { kind: "error"; message: string };

interface SubjectOption { id: string; label: string; desc: string; enabled: boolean; }

const SUBJECTS: SubjectOption[] = [
  { id: "math",      label: "Mathematics", desc: "Algebra, calculus, probability & geometry", enabled: true  },
  { id: "physics",   label: "Physics",     desc: "Coming soon",                                enabled: false },
  { id: "chemistry", label: "Chemistry",   desc: "Coming soon",                                enabled: false },
  { id: "biology",   label: "Biology",     desc: "Coming soon",                                enabled: false },
];

// ── Main Exam component ───────────────────────────────────────────────────────

export function Exam() {
  const [phase, setPhase] = useState<Phase>({ kind: "loading" });
  const [subject, setSubject] = useState("math");
  const abortRef = useRef<AbortController | null>(null);
  const token = getToken()!;

  useEffect(() => {
    getActiveSession(token).then((session) => {
      const exercises = session?.exam_content?.exercises ?? [];
      if (session && exercises.length > 0) {
        setPhase({ kind: "exam", exercises, sessionId: session.session_id });
      } else {
        setPhase({ kind: "setup" });
      }
    });
  }, [token]);

  const handleGenerate = useCallback(async () => {
    setPhase({ kind: "generating" });
    abortRef.current = new AbortController();
    let capturedSessionId = "";
    let done = false;
    let examReceived = false;
    try {
      const reader = await generateExamStream(token, abortRef.current.signal);
      const decoder = new TextDecoder();
      let buf = "";
      while (!done) {
        const { done: rdone, value } = await reader.read();
        if (rdone) break;
        buf += decoder.decode(value, { stream: true });
        const lines = buf.split("\n");
        buf = lines.pop() ?? "";
        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const raw = line.slice(6).trim();
          if (raw === "[DONE]") { done = true; break; }
          try {
            const payload = JSON.parse(raw) as Record<string, unknown>;
            if (payload.event === "session_created") {
              capturedSessionId = (payload.session_id as string) ?? "";
            } else if (payload.event === "exam_complete") {
              const content = payload.exam_content as { exercises?: ExamExercise[] } | undefined;
              const exercises = content?.exercises ?? [];
              examReceived = true;
              setPhase({ kind: "exam", exercises, sessionId: capturedSessionId });
            } else if (payload.event === "error") {
              setPhase({ kind: "error", message: (payload.message as string) || "Generation failed. Please try again." });
              done = true;
            }
          } catch { /* ignore */ }
        }
      }
      if (!examReceived) setPhase({ kind: "error", message: "Generation completed but no exam was received. Please try again." });
    } catch (err: unknown) {
      if ((err as Error).name === "AbortError") return;
      setPhase({ kind: "error", message: err instanceof Error ? err.message : "Unexpected error. Please try again." });
    }
  }, [token]);

  useEffect(() => () => { abortRef.current?.abort(); }, []);

  if (phase.kind === "loading") {
    return (
      <div className="page">
        <div className="page-head">
          <div className="sk" style={{ height: 32, width: 200, marginBottom: 10 }} />
          <div className="sk" style={{ height: 16, width: 320 }} />
        </div>
        {[0, 1, 2].map((i) => <div key={i} className="card sk" style={{ height: 120, marginBottom: 16 }} />)}
      </div>
    );
  }

  if (phase.kind === "setup") {
    return (
      <div className="page">
        <div className="page-head">
          <h1 className="page-title">Practice Exam</h1>
          <p className="page-sub">Generate a full 20-point mock exam in timed conditions. 3 hours.</p>
        </div>
        <div className="exam-setup">
          <p className="exam-section-label">Select a subject</p>
          <div className="subject-grid">
            {SUBJECTS.map((s) => (
              <button key={s.id}
                className={["subject-card", s.id === subject && s.enabled ? "subject-selected" : "", !s.enabled ? "subject-disabled" : ""].filter(Boolean).join(" ")}
                onClick={() => { if (s.enabled) setSubject(s.id); }} disabled={!s.enabled}>
                <span className="subject-name">{s.label}</span>
                <span className="subject-desc">{s.desc}</span>
              </button>
            ))}
          </div>
          <div className="exam-meta" style={{ marginBottom: 28 }}>
            <Pill kind="blue">20 points</Pill>
            <Pill kind="grey">3 hours</Pill>
            <Pill kind="green">5 exercises</Pill>
          </div>
          <button className="btn btn-blue" style={{ width: "100%" }} onClick={handleGenerate}>Generate Exam</button>
        </div>
      </div>
    );
  }

  if (phase.kind === "generating") {
    return (
      <div className="page">
        <div className="exam-generating">
          <div className="exam-spinner" />
          <h2 className="exam-gen-title">Generating your exam…</h2>
          <p className="exam-gen-sub">Crafting 5 exercises across your curriculum. This takes about 30 seconds.</p>
        </div>
      </div>
    );
  }

  if (phase.kind === "error") {
    return (
      <div className="page">
        <div className="page-head"><h1 className="page-title">Practice Exam</h1></div>
        <div className="card" style={{ padding: "28px 32px", maxWidth: 520 }}>
          <p style={{ margin: "0 0 12px", fontWeight: 700, color: "var(--tier-high)" }}>Generation failed</p>
          <p style={{ margin: "0 0 24px", fontSize: 14, color: "var(--ink-2)" }}>{phase.message}</p>
          <button className="btn btn-ghost" onClick={() => setPhase({ kind: "setup" })}>Try again</button>
        </div>
      </div>
    );
  }

  if (phase.kind === "taking") {
    return (
      <ExamTakingView
        sessionId={phase.sessionId}
        exercises={phase.exercises}
        token={token}
        onBack={() => setPhase({ kind: "exam", exercises: phase.exercises, sessionId: phase.sessionId })}
      />
    );
  }

  // exam preview phase
  const totalMarks = phase.exercises.reduce((s, ex) => s + ex.total_marks, 0);
  return (
    <div className="page">
      <div className="exam-top">
        <div>
          <h1 className="page-title">Mathematics — Mock Exam</h1>
          <p className="page-sub">Review the exam, then start when ready.</p>
        </div>
        <div className="exam-top-right">
          <div className="exam-meta">
            <Pill kind="blue">{totalMarks} pts</Pill>
          </div>
          <button className="btn btn-blue"
            onClick={() => setPhase({ kind: "taking", exercises: phase.exercises, sessionId: phase.sessionId })}>
            Start Exam
          </button>
          <button className="btn btn-ghost exam-export-btn" onClick={() => window.print()}>Export PDF</button>
        </div>
      </div>
      <div className="card exam-body">
        {phase.exercises.map((ex, idx) => (
          <div key={ex.id} className="exam-exercise">
            <div className="exam-exercise-header">
              <span className="exam-ex-num">Exercise {ROMAN[idx] ?? ex.id}</span>
              <span className="exam-ex-topic">{ex.topic}</span>
              <span className="exam-ex-marks">{ex.total_marks} pts</span>
            </div>
            <div className="exam-exercise-stem"><RichMath>{ex.content}</RichMath></div>
            {ex.parts.map((p) => (
              <div key={p.part} className="exam-part">
                <span className="exam-part-label">{p.part})</span>
                <div className="exam-part-content"><RichMath>{p.content}</RichMath></div>
                <span className="exam-part-marks">({p.marks} pt{p.marks !== 1 ? "s" : ""})</span>
              </div>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}

// ── GraphPanel (Desmos JS API) ─────────────────────────────────────────────────

function GraphPanel({ onUseGraph, onClose }: { onUseGraph: (text: string) => void; onClose: () => void }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const calcRef = useRef<DesmosCalculator | null>(null);

  useLayoutEffect(() => {
    if (!containerRef.current || !window.Desmos || calcRef.current) return;
    calcRef.current = window.Desmos.GraphingCalculator(containerRef.current, {
      keypad: true,
      expressions: true,
      settingsMenu: false,
      zoomButtons: true,
    });
    return () => {
      calcRef.current?.destroy();
      calcRef.current = null;
    };
  }, []);

  const handleUseGraph = () => {
    const exprs = calcRef.current
      ?.getExpressions()
      .filter((e): e is DesmosExpression & { latex: string } =>
        typeof e.latex === "string" && e.latex.trim().length > 0 && !e.hidden
      )
      .map((e) => e.latex.trim());

    if (!exprs?.length) {
      alert("Add some expressions in Desmos first.");
      return;
    }
    onUseGraph(`[Graph: ${exprs.join(", ")}]`);
  };

  return (
    <>
      <div className="desmos-panel-header">
        <span className="desmos-panel-title">Desmos Graphing Calculator</span>
        <button className="btn btn-ghost" style={{ padding: "4px 10px", fontSize: 16, lineHeight: 1 }} onClick={onClose}>✕</button>
      </div>
      <div ref={containerRef} className="graph-canvas" />
      <div className="graph-footer">
        <button className="btn btn-blue" style={{ width: "100%" }} onClick={handleUseGraph}>Use Graph →</button>
      </div>
    </>
  );
}

// ── ExamTakingView ────────────────────────────────────────────────────────────

interface GradingResult { score1: number; score2: number; average: number; discrepancy: boolean; }

function ExamTakingView({ sessionId, exercises, token, onBack }: {
  sessionId: string; exercises: ExamExercise[]; token: string; onBack: () => void;
}) {
  const [activeEx, setActiveEx] = useState(0);
  // answers keyed by "<exercise_id>__<part>" e.g. "1__1", "2__a"
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [graphOpen, setGraphOpen] = useState(false);
  const [graphLoaded, setGraphLoaded] = useState(false);
  const [lastFocusedKey, setLastFocusedKey] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<GradingResult | null>(null);
  const bodyRef = useRef<HTMLDivElement>(null);

  const answerKey = (exId: number, part: string) => `${exId}__${part}`;

  const goToExercise = (idx: number) => {
    setActiveEx(idx);
    bodyRef.current?.scrollTo({ top: 0, behavior: "smooth" });
  };

  const handleUseGraph = useCallback((text: string) => {
    const ex = exercises[activeEx];
    const fallbackKey = ex ? answerKey(ex.id, ex.parts[0]?.part ?? "1") : null;
    const targetKey = lastFocusedKey ?? fallbackKey;
    if (!targetKey) return;
    setAnswers((prev) => ({ ...prev, [targetKey]: (prev[targetKey] ?? "") + "\n" + text }));
  }, [lastFocusedKey, exercises, activeEx]);

  const toggleGraph = () => {
    if (!graphLoaded) setGraphLoaded(true);
    setGraphOpen((o) => !o);
  };

  const handleSubmit = async () => {
    const hasAny = Object.values(answers).some((v) => v.trim());
    if (!hasAny) { alert("Write at least one answer before submitting."); return; }
    if (!window.confirm("Submit your exam for grading? This cannot be undone.")) return;
    setSubmitting(true);
    try {
      const payload = exercises
        .map((ex) => ({
          exercise_id: ex.id,
          parts: ex.parts
            .filter((p) => (answers[answerKey(ex.id, p.part)] ?? "").trim())
            .map((p) => ({
              part: p.part,
              answer: answers[answerKey(ex.id, p.part)] ?? "",
              submitted_at: new Date().toISOString(),
            })),
        }))
        .filter((ex) => ex.parts.length > 0);

      const apiResult = await submitExamAnswers(token, sessionId, payload);
      setResult({
        score1: apiResult.evaluator_1.grand_total,
        score2: apiResult.evaluator_2.grand_total,
        average: apiResult.average_total,
        discrepancy: apiResult.discrepancy_flagged,
      });
    } catch (err) {
      alert(err instanceof Error ? err.message : "Submission failed. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  if (result) {
    return (
      <div className="page">
        <div className="page-head">
          <h1 className="page-title">Exam Submitted</h1>
          <p className="page-sub">Graded by two independent AI evaluators.</p>
        </div>
        <div className="card" style={{ padding: "32px 36px", maxWidth: 500 }}>
          <div className="grading-scores">
            <div className="grading-score-block">
              <div className="grading-score-label">Strict evaluator</div>
              <div className="grading-score-value">{result.score1.toFixed(1)}<span className="grading-score-denom"> / 20</span></div>
            </div>
            <div className="grading-score-divider" />
            <div className="grading-score-block">
              <div className="grading-score-label">Average</div>
              <div className="grading-score-value">{result.average.toFixed(1)}<span className="grading-score-denom"> / 20</span></div>
            </div>
            <div className="grading-score-divider" />
            <div className="grading-score-block">
              <div className="grading-score-label">Lenient evaluator</div>
              <div className="grading-score-value">{result.score2.toFixed(1)}<span className="grading-score-denom"> / 20</span></div>
            </div>
          </div>
          {result.discrepancy && (
            <p className="grading-discrepancy-note">Discrepancy detected between evaluators — a professor review may be warranted.</p>
          )}
          <button className="btn btn-ghost" style={{ marginTop: 24 }} onClick={onBack}>Back to exam</button>
        </div>
      </div>
    );
  }

  const ex = exercises[activeEx] ?? exercises[0];
  const answeredCount = exercises.filter((e) =>
    e.parts.some((p) => (answers[answerKey(e.id, p.part)] ?? "").trim())
  ).length;

  return (
    <div className={`taking-page${graphOpen ? " taking-desmos-open" : ""}`}>
      <div className="taking-bar">
        <div className="exercise-tabs">
          {exercises.map((e, i) => {
            const hasAnswer = e.parts.some((p) => (answers[answerKey(e.id, p.part)] ?? "").trim());
            return (
              <button key={e.id}
                className={`exercise-tab${activeEx === i ? " exercise-tab-active" : ""}${hasAnswer ? " exercise-tab-done" : ""}`}
                onClick={() => goToExercise(i)} title={e.topic}>
                {ROMAN[i] ?? e.id}
              </button>
            );
          })}
        </div>
        <div className="taking-bar-sep" />
        <div className="taking-bar-actions">
          <button
            className={`btn btn-ghost taking-desmos-btn${graphOpen ? " taking-desmos-btn-active" : ""}`}
            onClick={toggleGraph} title="Desmos graphing calculator">
            Desmos
          </button>
          <button className="btn btn-blue" onClick={handleSubmit} disabled={submitting}>
            {submitting ? "Grading…" : `Submit${answeredCount > 0 ? ` (${answeredCount}/${exercises.length})` : ""}`}
          </button>
        </div>
      </div>

      <div className="taking-body" ref={bodyRef}>
        {ex && (
          <>
            <div className="taking-ex-header">
              <span className="taking-ex-title">Exercise {ROMAN[activeEx] ?? ex.id} — {ex.topic}</span>
              <span className="taking-ex-marks">{ex.total_marks} pts</span>
            </div>
            <div className="taking-section">
              <div className="taking-question-content"><RichMath>{ex.content}</RichMath></div>
            </div>
            {ex.parts.map((part) => {
              const key = answerKey(ex.id, part.part);
              return (
                <div key={part.part} className="taking-section taking-section-q">
                  <div className="taking-question-content">
                    <span className="taking-part-num">{part.part})</span>
                    <RichMath>{part.content}</RichMath>
                    <span className="exam-part-marks" style={{ marginLeft: 6 }}>({part.marks} pt{part.marks !== 1 ? "s" : ""})</span>
                  </div>
                  <div className="taking-answer-wrap">
                    <span className="taking-answer-label">Your answer for part {part.part}</span>
                    <textarea className="taking-textarea" placeholder="Write your solution here…"
                      value={answers[key] ?? ""}
                      onChange={(e) => setAnswers((prev) => ({ ...prev, [key]: e.target.value }))}
                      onFocus={() => setLastFocusedKey(key)} />
                  </div>
                </div>
              );
            })}
            <div className="taking-ex-nav">
              <button className="btn btn-ghost" disabled={activeEx === 0} onClick={() => goToExercise(activeEx - 1)}>
                ← {activeEx > 0 ? `Exercise ${ROMAN[activeEx - 1]}` : ""}
              </button>
              <span className="taking-ex-nav-counter">{activeEx + 1} / {exercises.length}</span>
              <button className="btn btn-ghost" disabled={activeEx === exercises.length - 1} onClick={() => goToExercise(activeEx + 1)}>
                {activeEx < exercises.length - 1 ? `Exercise ${ROMAN[activeEx + 1]}` : ""} →
              </button>
            </div>
          </>
        )}
      </div>

      {graphLoaded && (
        <div className={`desmos-panel${graphOpen ? " desmos-panel-open" : ""}`}>
          <GraphPanel onUseGraph={handleUseGraph} onClose={() => setGraphOpen(false)} />
        </div>
      )}
    </div>
  );
}
