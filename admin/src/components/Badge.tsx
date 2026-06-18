import type { ReactNode } from "react";

interface BadgeProps {
  children: ReactNode;
  bg: string;
  color: string;
  dot?: boolean;
  className?: string;
}

export default function Badge({ children, bg, color, dot, className = "" }: BadgeProps) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11.5px] font-semibold ${className}`}
      style={{ background: bg, color }}
    >
      {dot && <span className="tfw-pulse h-1.5 w-1.5 rounded-full" style={{ background: color }} />}
      {children}
    </span>
  );
}

// ── Preset badges used across pages ──────────────────────────────────────────

export function StatusBadge({ status }: { status: "ingested" | "not-ingested" | "processing" | "queued" | "failed" }) {
  switch (status) {
    case "ingested":
      return <Badge bg="#3a4351" color="#fff">Ingested</Badge>;
    case "processing":
      return <Badge bg="#6b7688" color="#fff" dot>Processing</Badge>;
    case "queued":
      return <Badge bg="#d7dee8" color="#3a4351" dot>Queued</Badge>;
    case "failed":
      return <Badge bg="var(--danger-bg)" color="var(--on-danger)">Failed</Badge>;
    default:
      return <Badge bg="#eef1f6" color="#515b6b">Not ingested</Badge>;
  }
}

export function TierBadge({ tier }: { tier: "high" | "medium" | "low" }) {
  if (tier === "high") return <Badge bg="#262d39" color="#fff">High</Badge>;
  if (tier === "medium") return <Badge bg="#6b7688" color="#fff">Medium</Badge>;
  return <Badge bg="#d7dee8" color="#3a4351">Low</Badge>;
}

export function OnboardingBadge({ done }: { done: boolean }) {
  return done
    ? <Badge bg="#3a4351" color="#fff">Done</Badge>
    : <Badge bg="#eef1f6" color="#515b6b">Incomplete</Badge>;
}
