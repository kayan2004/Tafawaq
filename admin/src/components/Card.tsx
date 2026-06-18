import type { ReactNode } from "react";

interface CardProps {
  title?: string;
  caption?: string;
  children: ReactNode;
  className?: string;
}

export default function Card({ title, caption, children, className = "" }: CardProps) {
  return (
    <div
      className={`rounded-lg border overflow-hidden ${className}`}
      style={{ background: "var(--surface)", borderColor: "var(--line)" }}
    >
      {title && (
        <div className="flex items-baseline justify-between px-4 py-3" style={{ borderBottom: "1px solid var(--line)" }}>
          <div className="text-[14px] font-bold">{title}</div>
          {caption && <div className="text-[11.5px]" style={{ color: "var(--text-muted)" }}>{caption}</div>}
        </div>
      )}
      {children}
    </div>
  );
}
