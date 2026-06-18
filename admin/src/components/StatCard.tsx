interface StatCardProps {
  label: string;
  value: string | number;
  sublabel?: string;
}

export default function StatCard({ label, value, sublabel }: StatCardProps) {
  return (
    <div
      className="rounded-lg border py-[17px] px-[18px]"
      style={{ background: "var(--surface)", borderColor: "var(--line)", boxShadow: "var(--shadow-xs)" }}
    >
      <div
        className="text-[10.5px] font-bold uppercase tracking-[0.08em]"
        style={{ color: "var(--text-muted)" }}
      >
        {label}
      </div>
      <div
        className="mt-1.5 text-[26px] font-extrabold tracking-[-0.02em]"
        style={{ fontFamily: "var(--font-mono)" }}
      >
        {value}
      </div>
      {sublabel && (
        <div className="mt-1 text-[11.5px]" style={{ color: "var(--text-muted)" }}>
          {sublabel}
        </div>
      )}
    </div>
  );
}
