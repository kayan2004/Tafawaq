import { useCallback, useEffect, useState } from "react";
import { clearToken, getMe, getToken, setToken, type Me } from "./lib/api";
import Login from "./pages/Login";
import Sidebar, { type Section } from "./components/Sidebar";
import Overview from "./pages/Overview";
import Ingestion from "./pages/Ingestion";
import Topics from "./pages/Topics";
import Guardrails from "./pages/Guardrails";
import Users from "./pages/Users";

const THEME_KEY = "tfw-admin-theme";

type AuthState = "loading" | "anonymous" | "denied" | "authorized";

export default function App() {
  const [authState, setAuthState] = useState<AuthState>("loading");
  const [me, setMe] = useState<Me | null>(null);
  const [token, setTokenState] = useState<string | null>(null);
  const [section, setSection] = useState<Section>("overview");
  const [theme, setTheme] = useState<"light" | "dark">(
    () => (localStorage.getItem(THEME_KEY) === "dark" ? "dark" : "light"),
  );

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem(THEME_KEY, theme);
  }, [theme]);

  const checkAuth = useCallback(async (t: string) => {
    try {
      const profile = await getMe(t);
      if (profile.is_superuser) {
        setMe(profile);
        setTokenState(t);
        setAuthState("authorized");
      } else {
        clearToken();
        setAuthState("denied");
      }
    } catch {
      clearToken();
      setAuthState("anonymous");
    }
  }, []);

  useEffect(() => {
    const existing = getToken();
    if (!existing) {
      setAuthState("anonymous");
      return;
    }
    getMe(existing)
      .then((profile) => {
        if (profile.is_superuser) {
          setMe(profile);
          setTokenState(existing);
          setAuthState("authorized");
        } else {
          clearToken();
          setAuthState("denied");
        }
      })
      .catch(() => {
        clearToken();
        setAuthState("anonymous");
      });
  }, []);

  function handleLoggedIn(t: string) {
    setToken(t);
    void checkAuth(t);
  }

  if (authState === "loading") {
    return <div className="flex min-h-screen items-center justify-center" style={{ background: "var(--bg)" }} />;
  }

  if (authState === "denied") {
    return (
      <div className="flex min-h-screen items-center justify-center" style={{ background: "var(--bg)" }}>
        <div className="text-[15px] font-bold" style={{ color: "var(--text)" }}>Access denied</div>
      </div>
    );
  }

  if (authState === "anonymous" || !token || !me) {
    return <Login onLoggedIn={handleLoggedIn} />;
  }

  return (
    <div style={{ background: "var(--bg)", minHeight: "100vh" }}>
      <Sidebar
        active={section}
        onNavigate={setSection}
        email={me.email}
        theme={theme}
        onToggleTheme={() => setTheme((t) => (t === "light" ? "dark" : "light"))}
      />
      <div style={{ marginLeft: 220 }} className="flex min-h-screen flex-col">
        <main key={section} className="tfw-page-in flex-1" style={{ padding: "28px 32px 80px", maxWidth: 1320 }}>
          {section === "overview" && <Overview token={token} />}
          {section === "ingestion" && <Ingestion token={token} />}
          {section === "topics" && <Topics token={token} />}
          {section === "guardrails" && <Guardrails token={token} />}
          {section === "users" && <Users token={token} />}
        </main>
      </div>
    </div>
  );
}
