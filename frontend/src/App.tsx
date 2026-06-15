/* App.tsx — app shell: sidebar, mobile tab bar, hash routing. */
import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { Icons } from "./lib/icons";
import type { IconName } from "./lib/icons";
import { STUDENT } from "./data/mock";
import { Books } from "./pages/Books";
import { Chat } from "./pages/Chat";
import { ComingSoon } from "./pages/ComingSoon";
import { Dashboard } from "./pages/Dashboard";
import { Exam } from "./pages/Exam";
import { Login } from "./pages/Login";
import { Onboarding } from "./pages/Onboarding";
import { Topics } from "./pages/Topics";
import { getToken, clearToken, getMe, getUserDetails } from "./lib/api";
import type { UserDetails } from "./lib/api";
import type { PageId, PageProps } from "./types";

interface NavEntry {
  id: PageId;
  label: string;
  icon: IconName;
  tab?: boolean;
  disabled?: boolean;
}

const NAV: NavEntry[] = [
  { id: "dashboard", label: "Dashboard", icon: "dashboard", tab: true,  disabled: false },
  { id: "exam",      label: "Exams",     icon: "exam",      tab: true,  disabled: false },
  { id: "topics",    label: "Topics",    icon: "topics",    tab: true,  disabled: false },
  { id: "chat",      label: "Chat",      icon: "chat",      tab: true,  disabled: false },
  { id: "books",     label: "Books",     icon: "book",                  disabled: false },
];

const VALID_PAGES: PageId[] = ["dashboard", "exam", "topics", "chat", "results", "books"];

function isPageId(value: string): value is PageId {
  return (VALID_PAGES as string[]).includes(value);
}

const PLACEHOLDERS: Record<Exclude<PageId, "dashboard" | "chat" | "exam" | "books" | "topics">, { title: string; icon: IconName; blurb: string }> = {
  results: { title: "Results", icon: "scale", blurb: "Dual-evaluator grading with discrepancy highlighting. Coming soon." },
};

function renderPage(
  page: PageId,
  props: PageProps,
  onLogout: () => void,
  isAdmin: boolean,
  onCommand: (cmd: string) => void,
  triggerGenerate: boolean,
  onGenerateConsumed: () => void,
  isDark: boolean,
): ReactNode {
  if (page === "dashboard") return <Dashboard navigate={props.navigate} />;
  if (page === "chat") return <Chat onLogout={onLogout} isAdmin={isAdmin} onCommand={onCommand} isDark={isDark} />;
  if (page === "exam") return <Exam triggerGenerate={triggerGenerate} onGenerateConsumed={onGenerateConsumed} />;
  if (page === "books") return <Books />;
  if (page === "topics") return <Topics />;
  const p = PLACEHOLDERS[page as keyof typeof PLACEHOLDERS];
  if (!p) return <Chat onLogout={onLogout} isAdmin={isAdmin} onCommand={onCommand} />;
  return <ComingSoon title={p.title} icon={p.icon} blurb={p.blurb} />;
}

/* Minimal Moon/Sun SVG icons for theme toggle */
function MoonIcon() {
  return (
    <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
      <path d="M13.5 10A6 6 0 0 1 6 2.5a6 6 0 1 0 7.5 7.5z" />
    </svg>
  );
}
function SunIcon() {
  return (
    <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
      <circle cx="8" cy="8" r="3" />
      <line x1="8" y1="1" x2="8" y2="3" />
      <line x1="8" y1="13" x2="8" y2="15" />
      <line x1="1" y1="8" x2="3" y2="8" />
      <line x1="13" y1="8" x2="15" y2="8" />
      <line x1="3.05" y1="3.05" x2="4.46" y2="4.46" />
      <line x1="11.54" y1="11.54" x2="12.95" y2="12.95" />
      <line x1="12.95" y1="3.05" x2="11.54" y2="4.46" />
      <line x1="4.46" y1="11.54" x2="3.05" y2="12.95" />
    </svg>
  );
}

function PowerIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
      <path d="M8 2v5M5 4.27A5 5 0 1 0 11 4.27" />
    </svg>
  );
}

export default function App() {
  const [token, setToken] = useState<string | null>(() => getToken());
  const [isAdmin, setIsAdmin] = useState(false);
  const [needsOnboarding, setNeedsOnboarding] = useState(false);
  const [email, setEmail] = useState("");
  const [userName, setUserName] = useState<string | null>(null);
  const [theme, setTheme] = useState<"dark" | "light">(() => {
    try { return (localStorage.getItem("theme") as "dark" | "light") || "dark"; } catch { return "dark"; }
  });

  useEffect(() => {
    const t = getToken();
    if (t) {
      getMe(t).then((me) => { setIsAdmin(me.is_superuser); setUserName(me.name); }).catch(() => {});
      getUserDetails(t).then((d) => { if (d === null) setNeedsOnboarding(true); }).catch(() => {});
    }
  }, []);

  /* Persist + apply theme */
  useEffect(() => {
    try { localStorage.setItem("theme", theme); } catch { /* ignore */ }
    if (theme === "light") {
      document.documentElement.setAttribute("data-theme", "light");
    } else {
      document.documentElement.removeAttribute("data-theme");
    }
  }, [theme]);

  const handleLogin = (t: string, userEmail: string) => {
    setToken(t);
    setEmail(userEmail);
    getMe(t).then((me) => { setIsAdmin(me.is_superuser); setUserName(me.name); }).catch(() => {});
    getUserDetails(t).then((d) => { if (d === null) setNeedsOnboarding(true); }).catch(() => {});
  };
  const handleLogout = () => { clearToken(); setToken(null); setIsAdmin(false); setNeedsOnboarding(false); setEmail(""); setUserName(null); };
  const handleOnboardingComplete = (_details: UserDetails) => { setNeedsOnboarding(false); };

  const [page, setPage] = useState<PageId>(() => {
    const h = (location.hash || "").replace("#", "");
    return isPageId(h) ? h : "dashboard";
  });

  const [pendingGenerate, setPendingGenerate] = useState(false);

  const navigate = (id: PageId) => {
    setPage(id);
    window.scrollTo({ top: 0 });
  };

  const handleCommand = (cmd: string) => {
    if (cmd === "generate") setPendingGenerate(true);
  };
  const handleGenerateConsumed = () => setPendingGenerate(false);

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

  if (!token) return <Login onLogin={handleLogin} />;

  if (needsOnboarding) {
    return (
      <Onboarding token={token} email={email} onComplete={handleOnboardingComplete} />
    );
  }

  const isChat = page === "chat";
  const isBooks = page === "books";

  return (
    <div className="app">
      <aside className="sidebar">
        {/* Tafawwaq brand lockup — dark.png shown by default, light.png in day mode */}
        <div className="brand">
          <img src="/brand/tafawwaq-lockup-dark.png" alt="Tafawwaq" className="bm-lockup bm-dark" />
          <img src="/brand/tafawwaq-lockup-light.png" alt="Tafawwaq" className="bm-lockup bm-light" />
        </div>

        <nav className="nav">
          <div className="nav-eyebrow">
            <span className="micro">Navigation</span>
          </div>
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
                <span className="nav-ico"><I size={17} /></span>
                {n.label}
              </button>
            );
          })}
        </nav>

        <div className="nav-spacer" />

        {/* Day/Night theme toggle */}
        <div className="theme-toggle">
          <button
            className={`theme-opt ${theme === "dark" ? "active" : ""}`}
            onClick={() => setTheme("dark")}
            title="Night Lab"
          >
            <MoonIcon /> Night
          </button>
          <button
            className={`theme-opt ${theme === "light" ? "active" : ""}`}
            onClick={() => setTheme("light")}
            title="Day Lab"
          >
            <SunIcon /> Day
          </button>
        </div>

        <div className="user-card">
          <div className="avatar">
            {(userName || email || "?")
              .split(" ").filter(Boolean).slice(0, 2)
              .map((w) => w[0].toUpperCase()).join("") || "?"}
          </div>
          <div style={{ minWidth: 0, flex: 1 }}>
            <div className="user-name">{userName || email}</div>
            <div className="user-meta">{STUDENT.grade}</div>
          </div>
          <button className="logout-btn" onClick={handleLogout} title="Sign out">
            <PowerIcon />
          </button>
        </div>
      </aside>

      <main className={`main ${isChat ? "main-chat" : ""} ${isBooks ? "main-books" : ""}`}>
        {renderPage(page, { navigate }, handleLogout, isAdmin, handleCommand, pendingGenerate, handleGenerateConsumed, theme === "dark")}
      </main>

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
              <span className="nav-ico"><I size={22} /></span>
              {n.label.replace("Practice ", "")}
            </button>
          );
        })}
      </nav>
    </div>
  );
}
