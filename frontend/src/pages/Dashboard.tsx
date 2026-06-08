/* Dashboard.tsx — home page, ported from the prototype's pageHome.jsx. */
import type { CSSProperties } from "react";
import { Icons } from "../lib/icons";
import { tierOf } from "../lib/ui";
import { STUDENT, HISTORY, TOPICS } from "../data/mock";
import type { PageProps } from "../types";

export function Dashboard({ navigate }: PageProps) {
  const last = HISTORY[0];
  const topThree = [...TOPICS].sort((a, b) => b.count - a.count).slice(0, 4);

  return (
    <div className="page fade-up">
      <div className="page-head">
        <h1 className="page-title">Welcome back, {STUDENT.name.split(" ")[0]} 👋</h1>
        <p className="page-sub">42 days until the official GS Mathematics exam. Keep the streak going.</p>
      </div>

      {/* hero CTA */}
      <div className="hero card">
        <div className="hero-text">
          <span className="pill pill-blue" style={{ marginBottom: 14 }}>Recommended next</span>
          <h2 className="hero-title">Sit a full 3-hour mock</h2>
          <p className="hero-sub">Four exercises, 20 marks, graded instantly by two AI examiners. Weighted toward your weaker topics.</p>
          <div className="hero-actions">
            <button className="btn btn-green" onClick={() => navigate("exam")}><Icons.exam size={18} /> Start Practice Exam</button>
            <button className="btn btn-ghost" onClick={() => navigate("chat")}><Icons.chat size={17} /> Ask the coach</button>
          </div>
        </div>
        <div className="hero-stat">
          <div className="hero-stat-ring" style={{ "--p": `${(last.max / 20) * 360}deg` } as CSSProperties}>
            <div className="hero-stat-inner">
              <div className="hero-stat-num">{last.min}–{last.max}</div>
              <div className="hero-stat-lbl">last score</div>
            </div>
          </div>
        </div>
      </div>

      {/* stat tiles */}
      <div className="stat-grid">
        <div className="card stat-tile">
          <div className="stat-ico blue"><Icons.exam size={18} /></div>
          <div className="stat-num">{HISTORY.length}</div>
          <div className="stat-lbl">Mocks completed</div>
        </div>
        <div className="card stat-tile">
          <div className="stat-ico flame"><Icons.flame size={18} /></div>
          <div className="stat-num">{STUDENT.streak} days</div>
          <div className="stat-lbl">Study streak</div>
        </div>
        <div className="card stat-tile">
          <div className="stat-ico green"><Icons.target size={18} /></div>
          <div className="stat-num">14.5</div>
          <div className="stat-lbl">Avg. score / 20</div>
        </div>
        <div className="card stat-tile">
          <div className="stat-ico amber"><Icons.spark size={18} /></div>
          <div className="stat-num">128</div>
          <div className="stat-lbl">Questions practised</div>
        </div>
      </div>

      {/* two columns */}
      <div className="dash-cols">
        <div className="card dash-panel">
          <div className="dash-panel-head">
            <h3 className="dash-panel-title">Focus topics</h3>
            <button className="link-btn" onClick={() => navigate("topics")}>All topics →</button>
          </div>
          <div className="dash-topics">
            {topThree.map((t) => {
              const tier = tierOf(t.count);
              return (
                <button key={t.name} className="dash-topic" onClick={() => navigate("topics")}>
                  <span className={`tier-chip ${tier}`} />
                  <span className="dash-topic-name">{t.name}</span>
                  <span className="freq-track sm"><span className={`freq-fill ${tier}`} style={{ width: `${(t.count / 10) * 100}%` }} /></span>
                  <span className={`count-badge ${tier}`}>{t.count}<small>/10</small></span>
                </button>
              );
            })}
          </div>
        </div>

        <div className="card dash-panel">
          <div className="dash-panel-head">
            <h3 className="dash-panel-title">Recent attempts</h3>
            <button className="link-btn" onClick={() => navigate("history")}>History →</button>
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
