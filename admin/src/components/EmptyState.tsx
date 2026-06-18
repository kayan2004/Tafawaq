import type { ReactNode } from "react";
import { Icons, type IconName } from "../lib/icons";

interface EmptyStateProps {
  icon: IconName;
  heading: string;
  body?: string;
  action?: ReactNode;
}

export default function EmptyState({ icon, heading, body, action }: EmptyStateProps) {
  const Icon = Icons[icon];
  return (
    <div className="flex flex-col items-center text-center py-[72px] px-6">
      <Icon size={32} style={{ color: "var(--text-faint)" }} />
      <div className="mt-4 text-[15px] font-bold">{heading}</div>
      {body && (
        <div className="mt-2 max-w-[420px] text-[13px]" style={{ color: "var(--text-muted)" }}>
          {body}
        </div>
      )}
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}
