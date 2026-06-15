import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import {
  getToken,
  extractAnswers,
  getExamHistory,
  getExamSession,
  getExamResults,
  submitExamAnswers,
  getOfficialExams,
  takeOfficialExam,
  getOfficialExamPdfUrl,
  generateExamStream,
} from "../lib/api";
import type {
  ExamSessionSummary,
  ActiveExamSession,
  ExamExercise,
  OfficialExam,
  GradingApiResult,
  ExerciseResult,
  PartResult,
} from "../lib/api";
import { RichMath } from "../lib/math";
import { Pill, SubjectSelector } from "../lib/ui";

// Desmos JS API types (subset we use)
interface DesmosExpression { id: string; latex?: string; hidden?: boolean; }
interface DesmosCalculator { getExpressions(): DesmosExpression[]; destroy(): void; }
declare global {
  interface Window {
    Desmos?: { GraphingCalculator(el: HTMLElement, opts?: Record<string, unknown>): DesmosCalculator; };
  }
}

const ROMAN = ["I", "II", "III", "IV", "V", "VI"];

function formatDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });
}

function formatTime(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" });
}

// ── Score badge helper ────────────────────────────────────────────────────────

function scoreColor(score: number, max: number): string {
  if (max === 0) return "var(--ink-2)";
  const ratio = score / max;
  if (ratio >= 0.8) return "var(--green)";
  if (ratio >= 0.5) return "var(--amber, #d97706)";
  return "var(--red, #dc2626)";
}

// ── CorrectionView ─────────────────────────────────────────────────────────────

function CorrectionView({ result, onBack }: { result: GradingApiResult; onBack: () => void }) {
  const exercises = result.exam_content?.exercises ?? [];
  const ev1 = result.evaluator_1;

  const answerMap: Record<number, Record<string, string>> = {};
  for (const ex of result.student_answers ?? []) {
    answerMap[ex.exercise_id] = {};
    for (const p of ex.parts) {
      answerMap[ex.exercise_id][p.part] = p.answer;
    }
  }

  const resultsMap: Record<number, ExerciseResult> = {};
  for (const ex of ev1.exercises) {
    resultsMap[ex.exercise_id] = ex;
  }

  return (
    <div className="page">
      <div className="exam-top">
        <div>
          <button className="btn btn-ghost" style={{ marginBottom: 10, fontSize: 13 }} onClick={onBack}>
            ← Back to exams
          </button>
          <h1 className="page-title">Exam Results &amp; Corrections</h1>
          <p className="page-sub">Graded by two independent AI evaluators.</p>
        </div>
        <div className="exam-top-right">
          <div className="grading-scores" style={{ margin: 0 }}>
            <div className="grading-score-block">
              <div className="grading-score-label">Strict</div>
              <div className="grading-score-value" style={{ color: scoreColor(result.evaluator_1.grand_total, result.evaluator_1.grand_max) }}>
                {result.evaluator_1.grand_total.toFixed(1)}
                <span className="grading-score-denom"> / {result.evaluator_1.grand_max.toFixed(0)}</span>
              </div>
            </div>
            <div className="grading-score-divider" />
            <div className="grading-score-block">
              <div className="grading-score-label">Average</div>
              <div className="grading-score-value" style={{ color: scoreColor(result.average_total, result.evaluator_1.grand_max) }}>
                {result.average_total.toFixed(1)}
                <span className="grading-score-denom"> / {result.evaluator_1.grand_max.toFixed(0)}</span>
              </div>
            </div>
            <div className="grading-score-divider" />
            <div className="grading-score-block">
              <div className="grading-score-label">Lenient</div>
              <div className="grading-score-value" style={{ color: scoreColor(result.evaluator_2.grand_total, result.evaluator_2.grand_max) }}>
                {result.evaluator_2.grand_total.toFixed(1)}
                <span className="grading-score-denom"> / {result.evaluator_2.grand_max.toFixed(0)}</span>
              </div>
            </div>
          </div>
          {result.discrepancy_flagged && (
            <p className="grading-discrepancy-note" style={{ marginTop: 8, maxWidth: 260 }}>
              Evaluators disagreed by 2+ pts — professor review may be warranted.
            </p>
          )}
        </div>
      </div>

      {exercises.map((ex, idx) => {
        const exResult = resultsMap[ex.id];
        return (
          <div key={ex.id} className="card exam-body" style={{ marginBottom: 20 }}>
            <div className="exam-exercise-header" style={{ marginBottom: 12 }}>
              <span className="exam-ex-num">Exercise {ROMAN[idx] ?? ex.id}</span>
              <span className="exam-ex-topic">{ex.topic}</span>
              {exResult && (
                <span className="exam-ex-marks" style={{ color: scoreColor(exResult.exercise_total, exResult.exercise_max), fontWeight: 700 }}>
                  {exResult.exercise_total.toFixed(1)} / {exResult.exercise_max.toFixed(0)} pts
                </span>
              )}
            </div>
            {ex.content && (
              <div className="exam-exercise-stem" style={{ marginBottom: 16 }}>
                <RichMath>{ex.content}</RichMath>
              </div>
            )}
            <div className="exam-parts">
              {ex.parts.map((p) => {
                const partResult: PartResult | undefined = exResult?.parts[p.part];
                const studentAnswer = answerMap[ex.id]?.[p.part] ?? "";
                const isFullPart = p.part === "full";
                return (
                  <div key={p.part} className="correction-part">
                    {!isFullPart && (
                      <div className="exam-part-head" style={{ marginBottom: 8 }}>
                        <span className="exam-part-label">{p.part})</span>
                        <span className="exam-part-marks">{p.marks} pt{p.marks !== 1 ? "s" : ""}</span>
                        {partResult && (
                          <span
                            className="correction-part-score"
                            style={{ color: scoreColor(partResult.score, partResult.max_score) }}
                          >
                            {partResult.score.toFixed(1)} / {partResult.max_score.toFixed(1)}
                          </span>
                        )}
                      </div>
                    )}
                    <div className="exam-part-content" style={{ marginBottom: 10 }}>
                      <RichMath>{p.content}</RichMath>
                    </div>

                    <div className="correction-student-answer">
                      <div className="correction-label">Your answer</div>
                      <div className="correction-answer-text">
                        {studentAnswer.trim() ? (
                          <RichMath>{studentAnswer}</RichMath>
                        ) : (
                          <span style={{ color: "var(--ink-3)", fontStyle: "italic" }}>No answer submitted</span>
                        )}
                      </div>
                    </div>

                    {partResult && (
                      <>
                        {partResult.feedback && (
                          <div className="correction-feedback">
                            <span className="correction-label">Evaluator note</span>
                            <span className="correction-feedback-text">{partResult.feedback}</span>
                          </div>
                        )}
                        {partResult.correction && (
                          <div className="correction-solution">
                            <div className="correction-label correction-label-solution">Correction</div>
                            <div className="correction-solution-text">
                              <RichMath>{partResult.correction}</RichMath>
                            </div>
                          </div>
                        )}
                      </>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        );
      })}

      <button className="btn btn-ghost" style={{ marginBottom: 32 }} onClick={onBack}>
        ← Back to exams
      </button>
    </div>
  );
}

// ── Official exam detail view (embeds the PDF) ───────────────────────────────

function OfficialExamDetailView({ exam, starting, onStart, onBack, token }: {
  exam: OfficialExam; starting: boolean;
  onStart: () => void; onBack: () => void; token: string;
}) {
  const totalMarks = exam.exam_content?.exercises?.reduce((s, ex) => s + ex.total_marks, 0) ?? 0;
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [pdfError, setPdfError] = useState(false);
  const pdfUrlRef = useRef<string | null>(null);

  useEffect(() => {
    getOfficialExamPdfUrl(token, exam.id)
      .then((url) => { pdfUrlRef.current = url; setPdfUrl(url); })
      .catch(() => setPdfError(true));
    return () => { if (pdfUrlRef.current) URL.revokeObjectURL(pdfUrlRef.current); };
  }, [exam.id, token]);

  return (
    <div className="page">
      <div className="exam-top">
        <div>
          <button className="btn btn-ghost" style={{ marginBottom: 10, fontSize: 13 }} onClick={onBack}>
            ← Back to exams
          </button>
          <h1 className="page-title">Mathematics — {exam.year} {exam.session_label}</h1>
          <p className="page-sub">Lebanese GS Official Baccalaureate Exam</p>
        </div>
        <div className="exam-top-right">
          <div className="exam-meta">
            <Pill kind="blue">{totalMarks} pts</Pill>
            <Pill kind="green">Official</Pill>
          </div>
          <button className="btn btn-blue" onClick={onStart} disabled={starting}>
            {starting ? "Starting…" : "Start Exam"}
          </button>
        </div>
      </div>
      <div className="card exam-body" style={{ padding: 0, overflow: "hidden" }}>
        {pdfUrl ? (
          <iframe
            src={pdfUrl}
            style={{ width: "100%", height: "75vh", border: "none", display: "block" }}
            title={`${exam.year} ${exam.session_label} official exam`}
          />
        ) : pdfError ? (
          <div style={{ padding: "40px 32px", color: "var(--ink-2)", fontSize: 14 }}>
            PDF could not be loaded. Click <strong>Start Exam</strong> to begin.
          </div>
        ) : (
          <div className="sk" style={{ width: "100%", height: "75vh", borderRadius: 0 }} />
        )}
      </div>
    </div>
  );
}

// ── Shared exercise list renderer ─────────────────────────────────────────────

function ExerciseList({ exercises }: { exercises: ExamExercise[] }) {
  return (
    <>
      {exercises.map((ex, idx) => (
        <div key={ex.id} className="exam-exercise">
          <div className="exam-exercise-header">
            <span className="exam-ex-num">Exercise {ROMAN[idx] ?? ex.id}</span>
            <span className="exam-ex-topic">{ex.topic}</span>
            <span className="exam-ex-marks">{ex.total_marks} pts</span>
          </div>
          <div className="exam-exercise-stem"><RichMath>{ex.content}</RichMath></div>
          <div className="exam-parts">
            {ex.parts.map((p) => (
              <div key={p.part} className="exam-part">
                <div className="exam-part-head">
                  <span className="exam-part-label">{p.part})</span>
                  <span className="exam-part-marks">{p.marks} pt{p.marks !== 1 ? "s" : ""}</span>
                </div>
                <div className="exam-part-content"><RichMath>{p.content}</RichMath></div>
              </div>
            ))}
          </div>
        </div>
      ))}
    </>
  );
}

// ── Phase type ────────────────────────────────────────────────────────────────

type Phase =
  | { kind: "loading" }
  | { kind: "browse"; sessions: ExamSessionSummary[]; officialExams: OfficialExam[] }
  | { kind: "loading-detail" }
  | { kind: "detail"; session: ActiveExamSession; summary: ExamSessionSummary }
  | { kind: "results"; result: GradingApiResult; summary: ExamSessionSummary }
  | { kind: "official-detail"; exam: OfficialExam; starting: boolean }
  | { kind: "taking"; exercises: ExamExercise[]; sessionId: string; officialExamId?: string };

// ── Main Exam component ───────────────────────────────────────────────────────

interface ExamProps {
  triggerGenerate?: boolean;
  onGenerateConsumed?: () => void;
}

export function Exam({ triggerGenerate, onGenerateConsumed }: ExamProps) {
  const [phase, setPhase] = useState<Phase>({ kind: "loading" });
  const [generating, setGenerating] = useState(false);
  const [genError, setGenError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const token = getToken()!;

  const loadBrowse = () => {
    Promise.all([getExamHistory(token), getOfficialExams(token)]).then(
      ([sessions, officialExams]) => setPhase({ kind: "browse", sessions, officialExams })
    ).catch(() => setPhase({ kind: "browse", sessions: [], officialExams: [] }));
  };

  useEffect(() => { loadBrowse(); }, [token]);

  const startGenerate = async () => {
    setGenerating(true);
    setGenError(null);
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    let sessionId: string | null = null;
    try {
      const reader = await generateExamStream(token, ctrl.signal);
      const decoder = new TextDecoder();
      let buffer = "";
      outer: while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";
        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const payload = line.slice(6).trim();
          if (payload === "[DONE]") break outer;
          try {
            const ev = JSON.parse(payload);
            if (ev.event === "session_created") sessionId = ev.session_id;
            if (ev.event === "exam_complete" && sessionId) {
              const exercises: ExamExercise[] = ev.exam_content?.exercises ?? [];
              setPhase({ kind: "taking", exercises, sessionId });
              break outer;
            }
            if (ev.event === "error") {
              setGenError(ev.message ?? "Generation failed. Please try again.");
              break outer;
            }
          } catch { /* malformed SSE line */ }
        }
      }
    } catch (err) {
      if (err instanceof Error && err.name !== "AbortError") {
        setGenError(err.message);
      }
    } finally {
      setGenerating(false);
      abortRef.current = null;
    }
  };

  // Fire startGenerate once when triggered via /generate command from Chat.
  // genFiredRef prevents double-invocation under React StrictMode.
  const genFiredRef = useRef(false);
  useEffect(() => {
    if (!triggerGenerate || genFiredRef.current) return;
    genFiredRef.current = true;
    onGenerateConsumed?.();
    startGenerate();
  }, [triggerGenerate]); // eslint-disable-line react-hooks/exhaustive-deps

  const openDetail = async (summary: ExamSessionSummary) => {
    setPhase({ kind: "loading-detail" });
    if (summary.status === "graded") {
      const result = await getExamResults(token, summary.session_id);
      if (!result) { loadBrowse(); return; }
      setPhase({ kind: "results", result, summary });
      return;
    }
    const session = await getExamSession(token, summary.session_id);
    if (!session) { loadBrowse(); return; }
    setPhase({ kind: "detail", session, summary });
  };

  const openOfficialDetail = (exam: OfficialExam) => {
    setPhase({ kind: "official-detail", exam, starting: false });
  };

  const startOfficialExam = async (exam: OfficialExam) => {
    setPhase({ kind: "official-detail", exam, starting: true });
    try {
      const { session_id, exam_content } = await takeOfficialExam(token, exam.id);
      const exercises = (exam_content as { exercises?: ExamExercise[] }).exercises ?? [];
      setPhase({ kind: "taking", exercises, sessionId: session_id, officialExamId: exam.id });
    } catch {
      setPhase({ kind: "official-detail", exam, starting: false });
    }
  };

  const backToBrowse = () => {
    setPhase({ kind: "loading" });
    loadBrowse();
  };

  if (phase.kind === "loading" || phase.kind === "loading-detail") {
    return (
      <div className="page">
        <div className="page-head">
          <div className="sk" style={{ height: 32, width: 160, marginBottom: 10 }} />
          <div className="sk" style={{ height: 16, width: 300 }} />
        </div>
        {[0, 1, 2].map((i) => (
          <div key={i} className="card sk" style={{ height: 80, marginBottom: 12 }} />
        ))}
      </div>
    );
  }

  if (phase.kind === "taking") {
    return (
      <ExamTakingView
        sessionId={phase.sessionId}
        exercises={phase.exercises}
        token={token}
        onBack={backToBrowse}
        officialExamId={phase.officialExamId}
      />
    );
  }

  if (phase.kind === "results") {
    return <CorrectionView result={phase.result} onBack={backToBrowse} />;
  }

  if (phase.kind === "detail") {
    const { session, summary } = phase;
    const exercises = session.exam_content?.exercises ?? [];
    const totalMarks = exercises.reduce((s, ex) => s + ex.total_marks, 0);
    const canTake = summary.status === "in_progress";
    return (
      <div className="page">
        <div className="exam-top">
          <div>
            <button className="btn btn-ghost" style={{ marginBottom: 10, fontSize: 13 }} onClick={backToBrowse}>
              ← Back to exams
            </button>
            <h1 className="page-title">Mathematics — Mock Exam</h1>
            <p className="page-sub">{formatDate(summary.created_at)} at {formatTime(summary.created_at)}</p>
          </div>
          <div className="exam-top-right">
            <div className="exam-meta">
              <Pill kind="blue">{totalMarks} pts</Pill>
              {summary.status === "submitted" && <Pill kind="blue">Submitted</Pill>}
              {summary.status === "in_progress" && <Pill kind="grey">In Progress</Pill>}
            </div>
            {canTake && (
              <button
                className="btn btn-blue"
                onClick={() => setPhase({ kind: "taking", exercises, sessionId: session.session_id })}
              >
                Start Exam
              </button>
            )}
            <button className="btn btn-ghost exam-export-btn" onClick={() => window.print()}>Export PDF</button>
          </div>
        </div>
        <div className="card exam-body">
          <div className="exam-print-header">
            <p className="exam-print-title">Lebanese Official Baccalaureate — GS Mathematics</p>
            <p className="exam-print-meta">Mock Exam &nbsp;·&nbsp; {totalMarks} points &nbsp;·&nbsp; Duration: 3 hours</p>
            <p className="exam-print-instructions">Non-programmable calculator permitted. You may answer exercises in any order.</p>
          </div>
          <ExerciseList exercises={exercises} />
        </div>
      </div>
    );
  }

  if (phase.kind === "official-detail") {
    return (
      <OfficialExamDetailView
        exam={phase.exam}
        starting={phase.starting}
        onStart={() => startOfficialExam(phase.exam)}
        onBack={backToBrowse}
        token={token}
      />
    );
  }

  // browse phase
  const { sessions, officialExams } = phase;
  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1 className="page-title">Exams</h1>
          <p className="page-sub">Official Lebanese GS Baccalaureate exams and AI-generated mock exams.</p>
        </div>
        <SubjectSelector />
      </div>

      <div className="exam-section">
        <p className="exam-section-label">Official Exams</p>
        {officialExams.length === 0 ? (
          <div className="card" style={{ padding: "28px 32px", maxWidth: 560 }}>
            <p style={{ margin: 0, color: "var(--ink-2)", fontSize: 14 }}>
              Official Lebanese GS Mathematics Baccalaureate exams will appear here once uploaded.
            </p>
          </div>
        ) : (
          <div className="history-list">
            {officialExams.map((e) => {
              const totalMarks = e.exam_content?.exercises?.reduce((s, ex) => s + ex.total_marks, 0) ?? 20;
              return (
                <div key={e.id} className="card history-card">
                  <div className="history-card-left">
                    <span className="history-card-date">{e.year}</span>
                    <span className="history-card-time">{e.session_label}</span>
                  </div>
                  <div className="history-card-meta">
                    <Pill kind="blue">{totalMarks} pts</Pill>
                    <Pill kind="green">Official</Pill>
                  </div>
                  <button className="btn btn-ghost history-card-btn" onClick={() => openOfficialDetail(e)}>
                    View
                  </button>
                </div>
              );
            })}
          </div>
        )}
      </div>

      <div className="exam-section" style={{ marginTop: 36 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 14 }}>
          <p className="exam-section-label" style={{ margin: 0 }}>Generated Mock Exams</p>
          <button
            className="btn btn-green"
            style={{ fontSize: 13, padding: "6px 16px" }}
            onClick={startGenerate}
            disabled={generating}
          >
            {generating ? "Generating…" : "+ Generate New Exam"}
          </button>
        </div>
        {genError && (
          <div style={{ color: "var(--red, #dc2626)", fontSize: 13, marginBottom: 12 }}>
            {genError}
          </div>
        )}
        {generating && (
          <div className="card sk" style={{ height: 80, marginBottom: 12, maxWidth: 560 }} />
        )}
        {sessions.length === 0 && !generating ? (
          <div className="card" style={{ padding: "28px 32px", maxWidth: 560 }}>
            <p style={{ margin: 0, color: "var(--ink-2)", fontSize: 14 }}>
              No mock exams generated yet. Click <strong>+ Generate New Exam</strong> to get started.
            </p>
          </div>
        ) : (
          <div className="history-list">
            {sessions.map((s) => (
              <div key={s.session_id} className="card history-card">
                <div className="history-card-left">
                  <span className="history-card-date">{formatDate(s.created_at)}</span>
                  <span className="history-card-time">{formatTime(s.created_at)}</span>
                </div>
                <div className="history-card-meta">
                  <Pill kind="blue">Mathematics</Pill>
                  {s.status === "graded" && <Pill kind="green">Graded</Pill>}
                  {s.status === "submitted" && <Pill kind="blue">Submitted</Pill>}
                  {s.status === "in_progress" && <Pill kind="grey">In Progress</Pill>}
                </div>
                <button className="btn btn-ghost history-card-btn" onClick={() => openDetail(s)}>
                  {s.status === "in_progress" ? "Continue" : s.status === "graded" ? "Results" : "View"}
                </button>
              </div>
            ))}
          </div>
        )}
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

function ExamTakingView({ sessionId, exercises, token, onBack, officialExamId }: {
  sessionId: string; exercises: ExamExercise[]; token: string; onBack: () => void; officialExamId?: string;
}) {
  const [activeEx, setActiveEx] = useState(0);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const pdfUrlRef = useRef<string | null>(null);

  useEffect(() => {
    if (!officialExamId) return;
    getOfficialExamPdfUrl(token, officialExamId)
      .then((url) => { pdfUrlRef.current = url; setPdfUrl(url); })
      .catch(() => {});
    return () => { if (pdfUrlRef.current) URL.revokeObjectURL(pdfUrlRef.current); };
  }, [officialExamId, token]);

  const [graphOpen, setGraphOpen] = useState(false);
  const [graphLoaded, setGraphLoaded] = useState(false);
  const [lastFocusedKey, setLastFocusedKey] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [extracting, setExtracting] = useState(false);
  const [extractError, setExtractError] = useState<string | null>(null);
  const [result, setResult] = useState<GradingApiResult | null>(null);
  const bodyRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

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
      setResult(apiResult);
    } catch (err) {
      alert(err instanceof Error ? err.message : "Submission failed. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleExtract = async (file: File) => {
    setExtracting(true);
    setExtractError(null);
    try {
      const extracted = await extractAnswers(token, sessionId, file);
      setAnswers((prev) => {
        const next = { ...prev };
        for (const ex of extracted.answers ?? []) {
          for (const p of ex.parts ?? []) {
            next[answerKey(ex.exercise_id, p.part)] = p.answer;
          }
        }
        return next;
      });
    } catch (err) {
      setExtractError(err instanceof Error ? err.message : "Extraction failed. Please try again.");
    } finally {
      setExtracting(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  if (result) {
    return <CorrectionView result={result} onBack={onBack} />;
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
          {officialExamId && (
            <button
              className="btn btn-ghost"
              disabled={!pdfUrl}
              onClick={() => pdfUrl && window.open(pdfUrl, "_blank")}
              title="Open official exam PDF in a new tab">
              View PDF
            </button>
          )}
          <button
            className="btn btn-ghost"
            onClick={() => fileInputRef.current?.click()}
            disabled={extracting || submitting}
            title="Upload a photo or scan of your handwritten answers">
            {extracting ? "Extracting…" : "Upload answers"}
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept="image/jpeg,image/png,image/webp,application/pdf"
            style={{ display: "none" }}
            onChange={(e) => { const f = e.target.files?.[0]; if (f) handleExtract(f); }}
          />
          <button className="btn btn-blue" onClick={handleSubmit} disabled={submitting || extracting}>
            {submitting ? "Grading…" : `Submit${answeredCount > 0 ? ` (${answeredCount}/${exercises.length})` : ""}`}
          </button>
        </div>
      </div>

      <div className="taking-body" ref={bodyRef}>
        {extracting && (
          <div className="extraction-banner extraction-banner-loading">
            Extracting handwritten answers — this may take a few seconds…
          </div>
        )}
        {extractError && !extracting && (
          <div className="extraction-banner extraction-banner-error">
            {extractError}
            <button className="extraction-banner-dismiss" onClick={() => setExtractError(null)}>×</button>
          </div>
        )}
        {ex && (
          <>
            <div className="taking-ex-header">
              <span className="taking-ex-title">Exercise {ROMAN[activeEx] ?? ex.id} — {ex.topic}</span>
              <span className="taking-ex-marks">{ex.total_marks} pts</span>
            </div>
            {ex.content && (
              <div className="taking-section">
                <div className="taking-question-content"><RichMath>{ex.content}</RichMath></div>
              </div>
            )}
            {ex.parts.map((part) => {
              const key = answerKey(ex.id, part.part);
              const isFullPart = part.part === "full";
              return (
                <div key={part.part} className="taking-section taking-section-q">
                  {!isFullPart && (
                    <div className="taking-question-content">
                      <span className="taking-part-num">{part.part})</span>
                      <RichMath>{part.content}</RichMath>
                      <span className="exam-part-marks" style={{ marginLeft: 6 }}>({part.marks} pt{part.marks !== 1 ? "s" : ""})</span>
                    </div>
                  )}
                  <div className="taking-answer-wrap">
                    <span className="taking-answer-label">
                      {isFullPart ? `Your answer — Exercise ${ROMAN[activeEx] ?? ex.id} (${part.marks} pts)` : `Your answer for part ${part.part}`}
                    </span>
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
