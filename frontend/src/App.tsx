/* App.tsx — app shell: sidebar, mobile tab bar, hash routing. */
import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { Icons } from "./lib/icons";
import type { IconName } from "./lib/icons";
import { STUDENT } from "./data/mock";
import { Chat } from "./pages/Chat";
import { ComingSoon } from "./pages/ComingSoon";
import { Exam } from "./pages/Exam";
import { History } from "./pages/History";
import { Login } from "./pages/Login";
import { getToken, clearToken, getMe } from "./lib/api";
import type { PageId, PageProps } from "./types";

interface NavEntry {
  id: PageId;
  label: string;
  icon: IconName;
  tab?: boolean;
  disabled?: boolean;
}

// Only chat is active — all other tabs are temporarily disabled.
const NAV: NavEntry[] = [
  { id: "dashboard", label: "Dashboard",      icon: "dashboard", tab: true,  disabled: true  },
  { id: "exam",      label: "Practice Exam",  icon: "exam",      tab: true,  disabled: false },
  { id: "past",      label: "Past Questions", icon: "past",                  disabled: true  },
  { id: "topics",    label: "Topics",         icon: "topics",    tab: true,  disabled: true  },
  { id: "chat",      label: "Chat",           icon: "chat",      tab: true,  disabled: false },
  { id: "history",   label: "History",        icon: "history",   tab: true,  disabled: false },
];

const VALID_PAGES: PageId[] = ["dashboard", "exam", "past", "topics", "chat", "history", "results"];

function isPageId(value: string): value is PageId {
  return (VALID_PAGES as string[]).includes(value);
}

const PLACEHOLDERS: Record<Exclude<PageId, "dashboard" | "chat" | "exam" | "history">, { title: string; icon: IconName; blurb: string }> = {
  past:    { title: "Past Questions",   icon: "past",    blurb: "Retrieve real GS exam questions by topic from the archive. Coming soon." },
  topics:  { title: "Topics",           icon: "topics",  blurb: "Frequency analytics across the last 10 GS sessions. Coming soon." },
  results: { title: "Results",          icon: "scale",   blurb: "Dual-evaluator grading with discrepancy highlighting. Coming soon." },
};

function renderPage(page: PageId, _props: PageProps, onLogout: () => void, isAdmin: boolean): ReactNode {
  if (page === "chat" || page === "dashboard") return <Chat onLogout={onLogout} isAdmin={isAdmin} />;
  if (page === "exam") return <Exam />;
  if (page === "history") return <History />;
  const p = PLACEHOLDERS[page as keyof typeof PLACEHOLDERS];
  if (!p) return <Chat onLogout={onLogout} isAdmin={isAdmin} />;
  return <ComingSoon title={p.title} icon={p.icon} blurb={p.blurb} />;
}

export default function App() {
  const [token, setToken] = useState<string | null>(() => getToken());
  const [isAdmin, setIsAdmin] = useState(false);

  useEffect(() => {
    const t = getToken();
    if (t) getMe(t).then((me) => setIsAdmin(me.is_superuser)).catch(() => {});
  }, []);

  const handleLogin = (t: string) => {
    setToken(t);
    getMe(t).then((me) => setIsAdmin(me.is_superuser)).catch(() => {});
  };
  const handleLogout = () => { clearToken(); setToken(null); setIsAdmin(false); };

  const [page, setPage] = useState<PageId>(() => {
    const h = (location.hash || "").replace("#", "");
    // Default to chat; if hash is a valid non-disabled page honour it
    return isPageId(h) ? h : "chat";
  });

  const navigate = (id: PageId) => {
    setPage(id);
    window.scrollTo({ top: 0 });
  };

  useEffect(() => {
    if ((window.location.hash || "").replace("#", "") !== page) {
      window.location.hash = page;
    }
  }, [page]);

  useEffect(() => {
    const onHash = () => {
      const h = (window.location.hash || "").replace("#", "");
      if (isPageId(h)) setPage(h);
    };
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  // Not authenticated — show login gate (full screen, no shell)
  if (!token) {
    return <Login onLogin={handleLogin} />;
  }

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
              <button
                key={n.id}
                className={`nav-item ${page === n.id ? "active" : ""} ${n.disabled ? "nav-item-disabled" : ""}`}
                onClick={() => { if (!n.disabled) navigate(n.id); }}
                disabled={n.disabled}
                title={n.disabled ? "Coming soon" : undefined}
              >
                <I size={20} /> {n.label}
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
        {renderPage(page, { navigate }, handleLogout, isAdmin)}
      </main>

      {/* mobile bottom tab bar — chat only active */}
      <nav className="tabbar">
        {NAV.filter((n) => n.tab).map((n) => {
          const I = Icons[n.icon];
          return (
            <button
              key={n.id}
              className={`tab ${page === n.id ? "active" : ""} ${n.disabled ? "tab-disabled" : ""}`}
              onClick={() => { if (!n.disabled) navigate(n.id); }}
              disabled={n.disabled}
            >
              <I size={22} /> {n.label.replace("Practice ", "")}
            </button>
          );
        })}
      </nav>
    </div>
  );
}
