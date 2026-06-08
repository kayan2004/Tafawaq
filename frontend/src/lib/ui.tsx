/* ui.tsx — small shared UI helpers, ported from the prototype's lib.jsx.
   Mixes a component (Pill) with helpers (tierOf, tierLabel); fast-refresh's
   only-export-components rule does not apply to this shared module. */
/* eslint-disable react-refresh/only-export-components */
import type { CSSProperties, ReactNode } from "react";

export type PillKind = "grey" | "blue" | "green" | "amber" | "coral";

export function Pill({
  kind = "grey",
  children,
  style,
}: {
  kind?: PillKind;
  children: ReactNode;
  style?: CSSProperties;
}) {
  return <span className={`pill pill-${kind}`} style={style}>{children}</span>;
}

export type Tier = "high" | "mid" | "low";

export function tierOf(count: number): Tier {
  if (count >= 7) return "high";
  if (count >= 4) return "mid";
  return "low";
}

export const tierLabel: Record<Tier, string> = { high: "High", mid: "Medium", low: "Low" };
