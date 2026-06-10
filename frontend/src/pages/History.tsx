import { useEffect, useState } from "react";
import { getToken, getExamHistory, getExamSession } from "../lib/api";
import type { ExamSessionSummary, ActiveExamSession } from "../lib/api";
import { RichMath } from "../lib/math";
import { Pill } from "../lib/ui";

type View =
  | { kind: "loading" }
  | { kind: "list"; sessions: ExamSessionSummary[] }
  | { kind: "loading-detail" }
  | { kind: "detail"; session: ActiveExamSession; summary: ExamSessionSummary }
  | { kind: "empty" };

function formatDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });
}

function formatTime(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" });
}


export function History() {
  const [view, setView] = useState<View>({ kind: "loading" });
  const token = getToken()!;

  useEffect(() => {
    getExamHistory(token).then((sessions) => {
      if (sessions.length === 0) {
        setView({ kind: "empty" });
      } else {
        setView({ kind: "list", sessions });
      }
    });
  }, [token]);

  const openDetail = async (summary: ExamSessionSummary) => {
    setView({ kind: "loading-detail" });
    const session = await getExamSession(token, summary.session_id);
    if (!session) {
      setView((prev) =>
        prev.kind === "loading-detail"
          ? { kind: "list", sessions: [] }
          : prev
      );
      getExamHistory(token).then((sessions) =>
        setView({ kind: "list", sessions })
      );
      return;
    }
    setView({ kind: "detail", session, summary });
  };

  const backToList = () => {
    setView({ kind: "loading" });
    getExamHistory(token).then((sessions) => {
      setView(sessions.length === 0 ? { kind: "empty" } : { kind: "list", sessions });
    });
  };

  // ── Loading ──────────────────────────────────────────────────────────────────
  if (view.kind === "loading" || view.kind === "loading-detail") {
    return (
      <div className="page">
        <div className="page-head">
          <div className="sk" style={{ height: 32, width: 200, marginBottom: 10 }} />
          <div className="sk" style={{ height: 16, width: 320 }} />
        </div>
        {[0, 1, 2].map((i) => (
          <div key={i} className="card sk" style={{ height: 80, marginBottom: 12 }} />
        ))}
      </div>
    );
  }

  // ── Empty ────────────────────────────────────────────────────────────────────
  if (view.kind === "empty") {
    return (
      <div className="page">
        <div className="page-head">
          <h1 className="page-title">Exam History</h1>
          <p className="page-sub">Your generated mock exams appear here.</p>
        </div>
        <div className="card" style={{ padding: "40px 32px", textAlign: "center", maxWidth: 480 }}>
          <p style={{ margin: 0, color: "var(--ink-2)", fontSize: 14 }}>
            No exams generated yet. Head to the Practice Exam tab to create one.
          </p>
        </div>
      </div>
    );
  }

  // ── Detail view ──────────────────────────────────────────────────────────────
  if (view.kind === "detail") {
    const { session, summary } = view;
    const exercises = session.exam_content?.exercises ?? [];
    return (
      <div className="page">
        <div className="exam-top">
          <div>
            <button
              className="btn btn-ghost"
              style={{ marginBottom: 10, fontSize: 13 }}
              onClick={backToList}
            >
              ← Back to history
            </button>
            <h1 className="page-title">Mathematics — Mock Exam</h1>
            <p className="page-sub">{formatDate(summary.created_at)} at {formatTime(summary.created_at)}</p>
          </div>
          <div className="exam-top-right">
            <div className="exam-meta">
              <Pill kind="blue">20 pts</Pill>
              {summary.status === "graded" && <Pill kind="green">Graded</Pill>}
              {summary.status === "submitted" && <Pill kind="blue">Submitted</Pill>}
              {summary.status === "in_progress" && <Pill kind="grey">In Progress</Pill>}
            </div>
            <button className="btn btn-ghost exam-export-btn" onClick={() => window.print()}>
              Export PDF
            </button>
          </div>
        </div>

        <div className="card exam-body">
          {exercises.length > 0 ? (
            exercises.map((ex, idx) => (
              <div key={ex.id} className="exam-exercise">
                <div className="exam-exercise-header">
                  <span className="exam-ex-num">Exercise {["I","II","III","IV","V","VI"][idx] ?? ex.id}</span>
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
            ))
          ) : (
            <p style={{ color: "var(--ink-2)", fontSize: 14, margin: 0 }}>
              Exam content unavailable for this session.
            </p>
          )}
        </div>
      </div>
    );
  }

  // ── List view ────────────────────────────────────────────────────────────────
  const { sessions } = view;
  return (
    <div className="page">
      <div className="page-head">
        <h1 className="page-title">Exam History</h1>
        <p className="page-sub">{sessions.length} mock exam{sessions.length !== 1 ? "s" : ""} generated.</p>
      </div>

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
            <button
              className="btn btn-ghost history-card-btn"
              onClick={() => openDetail(s)}
            >
              View
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
