/* ResetPassword.tsx — set a new password from an emailed reset token. Styled to match Login.tsx. */
import { useState } from "react";
import { resetPassword } from "../lib/api";

interface Props {
  token: string;
  onSuccess: () => void;
}

export function ResetPassword({ token, onSuccess }: Props) {
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (password !== confirm) {
      setError("Passwords don't match");
      return;
    }
    setLoading(true);
    try {
      await resetPassword(token, password);
      onSuccess();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
      setLoading(false);
    }
  };

  return (
    <div className="login-wrap grid-bg">
      <div className="login-card card">
        <div className="login-brand">
          <img src="/brand/tafawwaq-glyph.png" alt="Tafawwaq" style={{ height: 52, width: "auto", margin: "0 auto 14px", display: "block" }} />
          <h1 className="login-title">Reset password</h1>
          <p className="login-sub">Choose a new password for your account</p>
        </div>

        <form onSubmit={submit} className="login-form">
          <label className="login-label">
            New password
            <input
              type="password"
              className="login-input"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              autoComplete="new-password"
              required
              autoFocus
            />
          </label>
          <label className="login-label">
            Confirm new password
            <input
              type="password"
              className="login-input"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              placeholder="••••••••"
              autoComplete="new-password"
              required
            />
          </label>

          {error && (
            <p className="login-error" role="alert">
              {error}
            </p>
          )}

          <button type="submit" className="btn btn-blue" style={{ width: "100%", marginTop: 4 }} disabled={loading}>
            {loading ? <span className="login-spinner" aria-hidden="true" /> : "Reset password"}
          </button>
        </form>
      </div>
    </div>
  );
}
