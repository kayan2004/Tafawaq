import { useState } from "react";
import { login } from "../lib/api";
import { Icons } from "../lib/icons";

interface LoginProps {
  onLoggedIn: (token: string) => void;
}

export default function Login({ onLoggedIn }: LoginProps) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const token = await login(email, password);
      onLoggedIn(token);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center" style={{ background: "var(--bg)" }}>
      <form
        onSubmit={handleSubmit}
        className="w-[360px] rounded-lg border p-6"
        style={{ background: "var(--surface)", borderColor: "var(--line)", boxShadow: "var(--shadow-md)" }}
      >
        <div className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-md" style={{ background: "var(--surface-3)" }}>
            <Icons.spark size={18} style={{ color: "var(--text-muted)" }} />
          </div>
          <div>
            <div className="text-[15px] font-extrabold tracking-[-0.01em]">Tafawwaq</div>
            <div className="text-[10px] font-bold uppercase tracking-[0.08em]" style={{ color: "var(--text-faint)" }}>
              Admin · Ops
            </div>
          </div>
        </div>

        <div className="mt-6 flex flex-col gap-3">
          <label className="flex flex-col gap-1.5">
            <span className="text-[11.5px] font-semibold" style={{ color: "var(--text-2)" }}>Email</span>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="h-[36px] rounded-md border px-3 text-[13px]"
              style={{ borderColor: "var(--line-strong)", background: "var(--surface)", color: "var(--text)" }}
            />
          </label>
          <label className="flex flex-col gap-1.5">
            <span className="text-[11.5px] font-semibold" style={{ color: "var(--text-2)" }}>Password</span>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="h-[36px] rounded-md border px-3 text-[13px]"
              style={{ borderColor: "var(--line-strong)", background: "var(--surface)", color: "var(--text)" }}
            />
          </label>
        </div>

        {error && (
          <div
            className="mt-4 rounded-md border px-3 py-2 text-[12.5px]"
            style={{ background: "var(--danger-bg)", borderColor: "var(--danger-line)", color: "var(--on-danger)" }}
          >
            {error}
          </div>
        )}

        <button
          type="submit"
          disabled={loading}
          className="mt-5 h-[36px] w-full rounded-md text-[13px] font-bold text-white disabled:opacity-60"
          style={{ background: "#262d39" }}
        >
          {loading ? "Signing in…" : "Sign in"}
        </button>
      </form>
    </div>
  );
}
