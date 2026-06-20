/* Dashboard.tsx — home page, Night Lab v2 redesign. */
import type { CSSProperties } from "react";
import { Icons } from "../lib/icons";
import { tierOf } from "../lib/ui";
import { STUDENT, HISTORY, TOPICS } from "../data/mock";
import type { PageProps } from "../types";

export function Dashboard({ navigate, userName }: PageProps & { userName: string | null }) {
  const last = HISTORY[0];
  const topFour = [...TOPICS].sort((a, b) => b.count - a.count).slice(0, 4);
  const firstName = userName?.trim().split(" ")[0] || "Student";

  /* ScoreRing: conic-gradient circle — accent arc for score fraction */
  const scorePercent = last.max / 20;
  const ringDeg = Math.round(scorePercent * 360);

  return (
    <div className="page fade-up">
      {/* Page head — title left, countdown chip right */}
      <div className="page-head">
        <div>
          <h1 className="page-title">Welcome back, {firstName}</h1>
          <p className="page-sub">Two evaluators, one curriculum. Keep the streak going.</p>
        </div>
        <div className="countdown-chip">
          <span className="cd-label">GS Math Exam</span>
          <span className="cd-num"><b>42</b><span>days left</span></span>
        </div>
      </div>

      {/* Hero CTA — graph-paper grid, ScoreRing on right */}
      <div className="hero card static grid-bg">
        <div className="hero-text">
          <div className="micro accent" style={{ marginBottom: 12 }}>Recommended next</div>
          <h2 className="hero-title">Sit a full 3-hour mock</h2>
          <p className="hero-sub">Four exercises, 20 marks, graded instantly by two AI examiners. Weighted toward your weaker topics.</p>
          <div className="hero-actions">
            <button className="btn btn-green" onClick={() => navigate("exam")}>
              <Icons.exam size={16} /> Start Practice Exam
            </button>
            <button className="btn btn-ghost" onClick={() => navigate("chat")}>
              <Icons.chat size={16} /> Ask the coach
            </button>
          </div>
        </div>
        {/* ScoreRing */}
        <div
          className="score-ring"
          style={{
            background: `conic-gradient(var(--accent) ${ringDeg}deg, var(--surface-2) 0)`,
          } as CSSProperties}
        >
          <div className="score-ring-inner">
            <div className="score-ring-num">{last.min}–{last.max}</div>
            <div className="score-ring-lbl">last score</div>
          </div>
        </div>
      </div>

      {/* Instrument-cluster stat strip — single panel, hairline-divided cells */}
      <div className="stat-grid">
        <div className="card stat-tile">
          <div className="stat-ico blue"><Icons.exam size={16} /></div>
          <div className="stat-num">{HISTORY.length}</div>
          <div className="stat-lbl">Mocks completed</div>
        </div>
        <div className="card stat-tile">
          <div className="stat-ico flame"><Icons.flame size={16} /></div>
          <div className="stat-num">{STUDENT.streak}<span style={{ fontSize: 15, color: "var(--muted)" }}>d</span></div>
          <div className="stat-lbl">Study streak</div>
        </div>
        <div className="card stat-tile">
          <div className="stat-ico green"><Icons.target size={16} /></div>
          <div className="stat-num">14.5</div>
          <div className="stat-lbl">Avg. score / 20</div>
        </div>
        <div className="card stat-tile">
          <div className="stat-ico amber"><Icons.spark size={16} /></div>
          <div className="stat-num">128</div>
          <div className="stat-lbl">Questions practised</div>
        </div>
      </div>

      {/* Two-column: topics + recent attempts */}
      <div className="dash-cols">
        <div className="card dash-panel">
          <div className="dash-panel-head">
            <h3 className="dash-panel-title">Focus topics</h3>
            <button className="link-btn" onClick={() => navigate("topics")}>All topics →</button>
          </div>
          <div className="dash-topics">
            {topFour.map((t) => {
              const tier = tierOf(t.count);
              return (
                <button key={t.name} className="dash-topic" onClick={() => navigate("topics")}>
                  <span className={`tier-chip ${tier}`} />
                  <span className="dash-topic-name">{t.name}</span>
                  <span className="freq-track sm" style={{ maxWidth: 80 }}>
                    <span className={`freq-fill ${tier}`} style={{ width: `${(t.count / 10) * 100}%` }} />
                  </span>
                  <span className={`count-badge ${tier}`}>{t.count}<small>/10</small></span>
                </button>
              );
            })}
          </div>
        </div>

        <div className="card dash-panel">
          <div className="dash-panel-head">
            <h3 className="dash-panel-title">Recent attempts</h3>
            <button className="link-btn" onClick={() => navigate("exam")}>All exams →</button>
          </div>
          <div className="dash-recent">
            {HISTORY.slice(0, 3).map((h) => (
              <button key={h.id} className="dash-recent-row" onClick={() => navigate("results")}>
                <div>
                  <div className="dash-recent-title">{h.title}</div>
                  <div className="dash-recent-date">{h.date}</div>
                </div>
                <span className="pill pill-grey">{h.min}–{h.max}<small style={{ opacity: .6 }}> /20</small></span>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
