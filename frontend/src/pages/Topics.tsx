import { useEffect, useState } from "react";
import { getQuestionsByTopic, getToken, getTopicStats } from "../lib/api";
import type { PastQuestion, TopicStat } from "../lib/api";
import { Icons } from "../lib/icons";
import { RichMath } from "../lib/math";
import { SubjectSelector } from "../lib/ui";

function tierCss(tier: string): string {
  return tier === "medium" ? "mid" : tier;
}

function sessionLabel(session: number): string {
  if (session === 0) return "Exceptional";
  if (session === 1) return "S1";
  return "S2";
}

function questionTypeLabel(questionType: string): string {
  return questionType.charAt(0).toUpperCase() + questionType.slice(1);
}

export function Topics() {
  const [topics, setTopics] = useState<TopicStat[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedTopic, setSelectedTopic] = useState<string | null>(null);

  useEffect(() => {
    const token = getToken();
    if (!token) { setLoading(false); return; }
    getTopicStats(token)
      .then((data) => setTopics([...data].sort((a, b) => b.appearances - a.appearances)))
      .catch(() => setError("Failed to load topic data."))
      .finally(() => setLoading(false));
  }, []);

  if (selectedTopic) {
    return <TopicQuestions topic={selectedTopic} onBack={() => setSelectedTopic(null)} />;
  }

  const visible = topics.filter((t) => t.topic !== "OTHER");
  const other   = topics.find((t) => t.topic === "OTHER");
  const maxAppearances = visible.length ? Math.max(...visible.map((t) => t.appearances)) : 1;

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1 className="page-title">Topics</h1>
          <p className="page-sub">Frequency analytics across GS exam history</p>
        </div>
        <SubjectSelector />
      </div>

      <div className="topics-callout">
        <Icons.target size={16} className="topics-callout-ico" />
        <span>
          Each row shows how many exam <b>exercises</b> tested that chapter.
          Higher appearances = higher priority for exam prep. Click a topic to see its questions.
        </span>
      </div>

      {loading && <p className="page-hint">Loading topics…</p>}
      {error  && <p className="page-hint">{error}</p>}

      {!loading && !error && topics.length === 0 && (
        <p className="page-hint">
          No topic data yet — run the ingestion pipeline to populate stats.
        </p>
      )}

      {!loading && !error && visible.length > 0 && (
        <div className="card static">
          <div className="topics-list">
            {visible.map((t) => {
              const tc = tierCss(t.frequency_tier);
              const pct = Math.round((t.appearances / maxAppearances) * 100);
              return (
                <button
                  key={t.topic}
                  type="button"
                  className="topic-row topic-row-clickable"
                  onClick={() => setSelectedTopic(t.topic)}
                >
                  <div className={`tier-chip ${tc}`} />
                  <div className="topic-row-body">
                    <div className="topic-row-top">
                      <span className="topic-row-name">{t.topic}</span>
                      <span className={`count-badge ${tc}`}>
                        {t.appearances} <small>× seen</small>
                      </span>
                    </div>
                    <div className="topic-row-bottom">
                      <div className="freq-track" style={{ flex: 1 }}>
                        <div className={`freq-fill ${tc}`} style={{ width: `${pct}%` }} />
                      </div>
                      <span className="topic-row-last">
                        Last: {t.last_seen_year} {sessionLabel(t.last_seen_session)}
                      </span>
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      )}

      {!loading && !error && other && (
        <p className="page-hint" style={{ paddingTop: 16, paddingBottom: 0 }}>
          + {other.appearances} exercises not yet mapped to a curriculum chapter.
        </p>
      )}
    </div>
  );
}

// ── Drill-down: questions for a single topic ───────────────────────────────────

function TopicQuestions({ topic, onBack }: { topic: string; onBack: () => void }) {
  const [questions, setQuestions] = useState<PastQuestion[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [revealed, setRevealed] = useState<Set<string>>(new Set());

  useEffect(() => {
    const token = getToken();
    if (!token) { setLoading(false); return; }
    setLoading(true);
    setError(null);
    getQuestionsByTopic(token, topic)
      .then((data) => setQuestions(
        [...data].sort((a, b) => b.year - a.year || b.session - a.session)
      ))
      .catch(() => setError("Failed to load questions for this topic."))
      .finally(() => setLoading(false));
  }, [topic]);

  const toggleAnswer = (chunkId: string) => {
    setRevealed((prev) => {
      const next = new Set(prev);
      if (next.has(chunkId)) next.delete(chunkId);
      else next.add(chunkId);
      return next;
    });
  };

  return (
    <div className="page">
      <button className="btn btn-ghost" style={{ marginBottom: 10, fontSize: 13 }} onClick={onBack}>
        ← Back to Topics
      </button>

      <div className="page-head">
        <div>
          <h1 className="page-title">{topic}</h1>
          <p className="page-sub">Past exam questions for this topic</p>
        </div>
      </div>

      {loading && <p className="page-hint">Loading questions…</p>}
      {error  && <p className="page-hint">{error}</p>}

      {!loading && !error && questions.length === 0 && (
        <p className="page-hint">No questions found for this topic yet.</p>
      )}

      {!loading && !error && questions.length > 0 && (
        <div className="card static">
          {questions.map((q) => (
            <div key={q.chunk_id} className="exam-exercise">
              <div className="exam-exercise-header">
                <span className="exam-ex-num">{q.year} {sessionLabel(q.session)}</span>
                <span className="exam-ex-topic">{questionTypeLabel(q.question_type)}</span>
                <span className="exam-ex-marks">{q.marks} pts</span>
              </div>
              <div className="exam-exercise-stem"><RichMath>{q.content}</RichMath></div>

              {q.answer && (
                <>
                  <button
                    type="button"
                    className="btn btn-ghost topic-q-answer-toggle"
                    onClick={() => toggleAnswer(q.chunk_id)}
                  >
                    {revealed.has(q.chunk_id) ? "Hide answer" : "Show answer"}
                  </button>
                  {revealed.has(q.chunk_id) && (
                    <div className="topic-q-answer">
                      <RichMath>{q.answer}</RichMath>
                    </div>
                  )}
                </>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
