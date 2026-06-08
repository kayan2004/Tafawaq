/* App.tsx — app shell: sidebar, mobile tab bar, hash routing.
   Ported from the prototype's app.jsx. The design-tool "Tweaks" panel is
   intentionally omitted (it is a prototyping affordance, not product UI).
   Routing uses the prototype's lightweight hash scheme; this can migrate to
   react-router-dom when auth and real pages are wired in. */
import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { Icons } from "./lib/icons";
import type { IconName } from "./lib/icons";
import { STUDENT } from "./data/mock";
import { Dashboard } from "./pages/Dashboard";
import { ComingSoon } from "./pages/ComingSoon";
import type { PageId, PageProps } from "./types";

interface NavEntry {
  id: PageId;
  label: string;
  icon: IconName;
  tab?: boolean;
}

const NAV: NavEntry[] = [
  { id: "dashboard", label: "Dashboard", icon: "dashboard", tab: true },
  { id: "exam", label: "Practice Exam", icon: "exam", tab: true },
  { id: "past", label: "Past Questions", icon: "past" },
  { id: "topics", label: "Topics", icon: "topics", tab: true },
  { id: "chat", label: "Chat", icon: "chat", tab: true },
  { id: "history", label: "History", icon: "history", tab: true },
];

const VALID_PAGES: PageId[] = ["dashboard", "exam", "past", "topics", "chat", "history", "results"];

function isPageId(value: string): value is PageId {
  return (VALID_PAGES as string[]).includes(value);
}

// Pages not yet ported render a friendly placeholder for now.
const PLACEHOLDERS: Record<Exclude<PageId, "dashboard">, { title: string; icon: IconName; blurb: string }> = {
  exam: { title: "Practice Exam", icon: "exam", blurb: "Generate a full 3-hour mock exam with live KaTeX rendering. Coming soon." },
  past: { title: "Past Questions", icon: "past", blurb: "Retrieve real GS exam questions by topic from the archive. Coming soon." },
  topics: { title: "Topics", icon: "topics", blurb: "Frequency analytics across the last 10 GS sessions. Coming soon." },
  chat: { title: "Chat", icon: "chat", blurb: "Ask the AI coach, with streaming answers and math rendering. Coming soon." },
  history: { title: "History", icon: "history", blurb: "Review your past attempts and score ranges. Coming soon." },
  results: { title: "Results", icon: "scale", blurb: "Dual-evaluator grading with discrepancy highlighting. Coming soon." },
};

function renderPage(page: PageId, props: PageProps): ReactNode {
  if (page === "dashboard") return <Dashboard {...props} />;
  const p = PLACEHOLDERS[page];
  return <ComingSoon title={p.title} icon={p.icon} blurb={p.blurb} />;
}

export default function App() {
  const [page, setPage] = useState<PageId>(() => {
    const h = (location.hash || "").replace("#", "");
    return isPageId(h) ? h : "dashboard";
  });

  const navigate = (id: PageId) => {
    setPage(id);
    window.scrollTo({ top: 0 });
  };

  // Keep the URL hash in sync with the active page (side effect lives in an effect).
  useEffect(() => {
    if ((window.location.hash || "").replace("#", "") !== page) {
      window.location.hash = page;
    }
  }, [page]);

  // React to back/forward and manual hash edits.
  useEffect(() => {
    const onHash = () => {
      const h = (window.location.hash || "").replace("#", "");
      if (isPageId(h)) setPage(h);
    };
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  const isChat = page === "chat";

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">∑</div>
          <div>
            <div className="brand-name">Math Coach</div>
            <div className="brand-sub">Lebanese GS Bac</div>
          </div>
        </div>

        <nav className="nav">
          {NAV.map((n) => {
            const I = Icons[n.icon];
            return (
              <button key={n.id} className={`nav-item ${page === n.id ? "active" : ""}`} onClick={() => navigate(n.id)}>
                <I size={20} /> {n.label}
                {n.id === "history" && page !== "history" && <span className="nav-badge">1</span>}
              </button>
            );
          })}
        </nav>

        <div className="nav-spacer" />

        <div className="user-card">
          <div className="avatar">{STUDENT.initials}</div>
          <div style={{ minWidth: 0 }}>
            <div className="user-name">{STUDENT.name}</div>
            <div className="user-meta">{STUDENT.grade}</div>
          </div>
        </div>
      </aside>

      <main className={`main ${isChat ? "main-chat" : ""}`}>
        {renderPage(page, { navigate })}
      </main>

      {/* mobile bottom tab bar — 5 main items */}
      <nav className="tabbar">
        {NAV.filter((n) => n.tab).map((n) => {
          const I = Icons[n.icon];
          return (
            <button key={n.id} className={`tab ${page === n.id ? "active" : ""}`} onClick={() => navigate(n.id)}>
              <I size={22} /> {n.label.replace("Practice ", "")}
            </button>
          );
        })}
      </nav>
    </div>
  );
}
