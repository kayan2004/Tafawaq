/* Login.tsx — auth gate: login or register before entering the app. */
import { useState } from "react";
import { login, register, setToken } from "../lib/api";
import { Icons } from "../lib/icons";

interface Props {
  onLogin: (token: string, email: string) => void;
}

export function Login({ onLogin }: Props) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      if (mode === "register") {
        await register(email, password);
      }
      const token = await login(email, password);
      setToken(token);
      onLogin(token, email);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  };

  const switchMode = () => {
    setMode((m) => (m === "login" ? "register" : "login"));
    setError("");
  };

  const EyeIcon = showPassword ? Icons["eye-off"] : Icons.eye;

  return (
    <div className="login-wrap grid-bg">
      <div className="login-card card">
        <div className="login-brand">
          <img src="/brand/tafawwaq-glyph.png" alt="Tafawwaq" style={{ height: 52, width: "auto", margin: "0 auto 14px", display: "block" }} />
          <h1 className="login-title">{mode === "login" ? "Welcome back" : "Create account"}</h1>
          <p className="login-sub">Lebanese GS Math · Baccalaureate Prep</p>
        </div>

        <form onSubmit={submit} className="login-form">
          <label className="login-label">
            Email
            <input
              type="email"
              className="login-input"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              autoComplete="email"
              required
              autoFocus
            />
          </label>
          <label className="login-label">
            Password
            <div className="login-password-wrap">
              <input
                type={showPassword ? "text" : "password"}
                className="login-input"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                autoComplete={mode === "login" ? "current-password" : "new-password"}
                required
              />
              <button
                type="button"
                className="login-password-toggle"
                onClick={() => setShowPassword((s) => !s)}
                aria-label={showPassword ? "Hide password" : "Show password"}
              >
                <EyeIcon size={16} className="" />
              </button>
            </div>
          </label>

          {error && (
            <p className="login-error" role="alert">
              {error}
            </p>
          )}

          <button
            type="submit"
            className="btn btn-blue"
            style={{ width: "100%", marginTop: 4 }}
            disabled={loading}
          >
            {loading ? (
              <span className="login-spinner" aria-hidden="true" />
            ) : mode === "login" ? "Sign in" : "Create account & sign in"}
          </button>
        </form>

        <p className="login-toggle">
          {mode === "login" ? "No account yet?" : "Already have an account?"}{" "}
          <button type="button" className="link-btn" onClick={switchMode}>
            {mode === "login" ? "Register" : "Sign in"}
          </button>
        </p>
      </div>
    </div>
  );
}
