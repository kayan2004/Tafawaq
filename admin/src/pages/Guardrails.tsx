import { useEffect, useState } from "react";
import { getGuardrailsMessages, getGuardrailsSummary, type GuardrailMessage, type GuardrailsSummary } from "../lib/api";
import StatCard from "../components/StatCard";
import Card from "../components/Card";
import EmptyState from "../components/EmptyState";
import { Icons } from "../lib/icons";

export default function Guardrails({ token }: { token: string }) {
  const [summary, setSummary] = useState<GuardrailsSummary | null>(null);
  const [messages, setMessages] = useState<GuardrailMessage[]>([]);

  useEffect(() => {
    void getGuardrailsSummary(token).then(setSummary);
    void getGuardrailsMessages(token).then(setMessages);
  }, [token]);

  return (
    <div>
      <h1 className="text-[20px] font-extrabold tracking-[-0.02em]">Guardrail analytics</h1>
      <p className="mt-1 text-[13px] font-medium" style={{ color: "var(--text-muted)" }}>
        Read-only audit log of blocked and warned messages. Last 7 days.
      </p>

      {summary && (
        <div className="mt-5 grid grid-cols-4 gap-3.5">
          <StatCard label="Messages (7d)" value={summary.messages_7d} />
          <StatCard label="Blocked" value={summary.blocked} />
          <StatCard label="Warned" value={summary.warned} />
          <StatCard label="Block rate" value={`${Math.round(summary.block_rate * 100)}%`} />
        </div>
      )}

      <div
        className="mt-4 flex items-center gap-2 rounded-md border px-3.5 py-2.5"
        style={{ background: "var(--surface-2)", borderColor: "var(--line)" }}
      >
        <Icons.shield size={15} style={{ color: "var(--text-muted)" }} />
        <span className="text-[12.5px]" style={{ color: "var(--text-2)" }}>
          0–1 normal · 2 = warning · 3+ = block · messages &lt; 10 words skip classification
        </span>
      </div>

      <Card className="mt-5">
        {messages.length === 0 ? (
          <EmptyState
            icon="shield"
            heading="No audit data yet"
            body="Guardrail tier and score persistence is being reworked — this section will populate once that lands."
          />
        ) : (
          <table className="w-full border-collapse">
            <thead>
              <tr>
                <th className="px-4 py-2.5 text-left text-[11px] font-bold uppercase tracking-[0.07em]" style={{ color: "var(--text-muted)", borderBottom: "1px solid var(--line)" }}>Timestamp</th>
                <th className="px-4 py-2.5 text-left text-[11px] font-bold uppercase tracking-[0.07em]" style={{ color: "var(--text-muted)", borderBottom: "1px solid var(--line)" }}>Message</th>
                <th className="px-4 py-2.5 text-left text-[11px] font-bold uppercase tracking-[0.07em]" style={{ color: "var(--text-muted)", borderBottom: "1px solid var(--line)" }}>Score</th>
                <th className="px-4 py-2.5 text-left text-[11px] font-bold uppercase tracking-[0.07em]" style={{ color: "var(--text-muted)", borderBottom: "1px solid var(--line)" }}>Level</th>
                <th className="px-4 py-2.5 text-left text-[11px] font-bold uppercase tracking-[0.07em]" style={{ color: "var(--text-muted)", borderBottom: "1px solid var(--line)" }}>Reason</th>
              </tr>
            </thead>
            <tbody>
              {messages.map((m, i) => (
                <tr key={i}>
                  <td className="px-4 py-3 text-[13px]" style={{ borderTop: "1px solid var(--line)", fontFamily: "var(--font-mono)" }}>{m.ts}</td>
                  <td className="px-4 py-3 max-w-[320px] truncate text-[13px]" style={{ borderTop: "1px solid var(--line)" }}>&ldquo;{m.text}&rdquo;</td>
                  <td className="px-4 py-3 text-[13px]" style={{ borderTop: "1px solid var(--line)", fontFamily: "var(--font-mono)", fontWeight: 700 }}>{m.score.toFixed(2)}</td>
                  <td className="px-4 py-3 text-[13px]" style={{ borderTop: "1px solid var(--line)" }}>{m.level}</td>
                  <td className="px-4 py-3 text-[13px]" style={{ borderTop: "1px solid var(--line)" }}>{m.reason}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>

      <div className="mt-3 flex items-center gap-1.5 text-[11.5px]" style={{ color: "var(--text-faint)" }}>
        <Icons.eye size={13} />
        Read-only audit log · message text is stored hashed; only the truncation above is surfaced here.
      </div>
    </div>
  );
}
