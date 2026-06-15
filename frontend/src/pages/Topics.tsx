import { useEffect, useState } from "react";
import { getToken, getTopicStats } from "../lib/api";
import type { TopicStat } from "../lib/api";
import { Icons } from "../lib/icons";
import { SubjectSelector } from "../lib/ui";

function tierCss(tier: string): string {
  return tier === "medium" ? "mid" : tier;
}

function sessionLabel(session: number): string {
  if (session === 0) return "Exceptional";
  if (session === 1) return "S1";
  return "S2";
}

export function Topics() {
  const [topics, setTopics] = useState<TopicStat[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = getToken();
    if (!token) { setLoading(false); return; }
    getTopicStats(token)
      .then((data) => setTopics([...data].sort((a, b) => b.appearances - a.appearances)))
      .catch(() => setError("Failed to load topic data."))
      .finally(() => setLoading(false));
  }, []);

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
          Higher appearances = higher priority for exam prep.
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
                <div key={t.topic} className="topic-row">
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
                </div>
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
