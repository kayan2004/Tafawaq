/* ForgotPassword.tsx — request a password reset email. Styled to match Login.tsx. */
import { useState } from "react";
import { forgotPassword } from "../lib/api";

interface Props {
  onBackToLogin: () => void;
}

export function ForgotPassword({ onBackToLogin }: Props) {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      await forgotPassword(email);
    } finally {
      setLoading(false);
      setSubmitted(true);
    }
  };

  return (
    <div className="login-wrap grid-bg">
      <div className="login-card card">
        <div className="login-brand">
          <img src="/brand/tafawwaq-glyph.png" alt="Tafawwaq" style={{ height: 52, width: "auto", margin: "0 auto 14px", display: "block" }} />
          <h1 className="login-title">Forgot password?</h1>
          <p className="login-sub">We'll email you a link to reset it</p>
        </div>

        {submitted ? (
          <div className="login-form">
            <p className="login-sub" style={{ textAlign: "center" }}>
              If an account exists for that email, we've sent password reset instructions.
            </p>
            <button type="button" className="btn btn-blue" style={{ width: "100%", marginTop: 4 }} onClick={onBackToLogin}>
              Back to sign in
            </button>
          </div>
        ) : (
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

            <button type="submit" className="btn btn-blue" style={{ width: "100%", marginTop: 4 }} disabled={loading}>
              {loading ? <span className="login-spinner" aria-hidden="true" /> : "Send reset link"}
            </button>
          </form>
        )}

        <p className="login-toggle">
          <button type="button" className="link-btn" onClick={onBackToLogin}>
            Back to sign in
          </button>
        </p>
      </div>
    </div>
  );
}
