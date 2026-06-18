import { useEffect, useMemo, useState } from "react";
import { deactivateUser, listUsers, type AdminUser } from "../lib/api";
import StatCard from "../components/StatCard";
import Card from "../components/Card";
import Button from "../components/Button";
import Modal from "../components/Modal";
import { OnboardingBadge } from "../components/Badge";

export default function Users({ token }: { token: string }) {
  const [users, setUsers] = useState<AdminUser[] | null>(null);
  const [target, setTarget] = useState<AdminUser | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    void listUsers(token).then(setUsers);
  }, [token]);

  const stats = useMemo(() => {
    if (!users) return null;
    const total = users.length;
    const active = users.filter((u) => u.is_active).length;
    const onboarded = users.filter((u) => u.onboarded).length;
    const totalExams = users.reduce((sum, u) => sum + u.exam_count, 0);
    return {
      total,
      active,
      inactive: total - active,
      onboardingRate: total ? Math.round((onboarded / total) * 100) : 0,
      avgExams: total ? (totalExams / total).toFixed(1) : "0",
      totalExams,
    };
  }, [users]);

  async function confirmDeactivate() {
    if (!target) return;
    setBusy(true);
    try {
      await deactivateUser(token, target.id);
      setUsers((prev) => prev?.map((u) => (u.id === target.id ? { ...u, is_active: false } : u)) ?? null);
      setTarget(null);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <h1 className="text-[20px] font-extrabold tracking-[-0.02em]">User management</h1>
      <p className="mt-1 text-[13px] font-medium" style={{ color: "var(--text-muted)" }}>
        Registered students, onboarding status, and exam activity.
      </p>

      {stats && (
        <div className="mt-5 grid grid-cols-3 gap-3.5">
          <StatCard label="Total users" value={stats.total} sublabel={`${stats.active} active · ${stats.inactive} inactive`} />
          <StatCard label="Onboarding complete" value={`${stats.onboardingRate}%`} />
          <StatCard label="Avg exams per user" value={stats.avgExams} sublabel={`${stats.totalExams} total`} />
        </div>
      )}

      {users && (
        <Card className="mt-5">
          <table className="w-full border-collapse">
            <thead>
              <tr>
                {["Email", "Registered", "Last login", "Onboarding", "Exams", "Avg score", "Actions"].map((h, i) => (
                  <th
                    key={h}
                    className={`px-4 py-2.5 text-[11px] font-bold uppercase tracking-[0.07em] ${i >= 4 && i <= 5 ? "text-right" : "text-left"}`}
                    style={{ color: "var(--text-muted)", borderBottom: "1px solid var(--line)" }}
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id}>
                  <td className="px-4 py-3 text-[13px]" style={{ borderTop: "1px solid var(--line)", fontFamily: "var(--font-mono)" }}>{u.email}</td>
                  <td className="px-4 py-3 text-[13px]" style={{ borderTop: "1px solid var(--line)" }}>{new Date(u.created_at).toLocaleDateString()}</td>
                  <td className="px-4 py-3 text-[13px]" style={{ borderTop: "1px solid var(--line)" }}>
                    {u.last_login ? new Date(u.last_login).toLocaleDateString() : "—"}
                  </td>
                  <td className="px-4 py-3 text-[13px]" style={{ borderTop: "1px solid var(--line)" }}>
                    <OnboardingBadge done={u.onboarded} />
                  </td>
                  <td className="px-4 py-3 text-right text-[13px]" style={{ borderTop: "1px solid var(--line)", fontFamily: "var(--font-mono)" }}>{u.exam_count}</td>
                  <td className="px-4 py-3 text-right text-[13px] font-semibold" style={{ borderTop: "1px solid var(--line)", fontFamily: "var(--font-mono)" }}>
                    {u.avg_score !== null ? u.avg_score.toFixed(1) : "—"}
                  </td>
                  <td className="px-4 py-3 text-[13px]" style={{ borderTop: "1px solid var(--line)" }}>
                    {u.is_active ? (
                      <Button variant="danger" onClick={() => setTarget(u)}>Deactivate</Button>
                    ) : (
                      <span style={{ color: "var(--text-faint)" }}>Inactive</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}

      <Modal
        open={target !== null}
        title={`Deactivate ${target?.email ?? ""}?`}
        body="The user will lose access immediately. Their exam history and progress data are retained. This action can be reversed by re-activating the account."
        confirmLabel="Deactivate account"
        tone="danger"
        confirmDisabled={busy}
        onConfirm={confirmDeactivate}
        onClose={() => setTarget(null)}
      />
    </div>
  );
}
