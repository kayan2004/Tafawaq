/* ui.tsx — small shared UI helpers, ported from the prototype's lib.jsx.
   Mixes a component (Pill) with helpers (tierOf, tierLabel); fast-refresh's
   only-export-components rule does not apply to this shared module. */
/* eslint-disable react-refresh/only-export-components */
import { useState, useEffect, useRef } from "react";
import type { CSSProperties, ReactNode } from "react";
import { Icons } from "./icons";

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

const SUBJECT_OPTIONS = [{ id: "math-gs12", label: "Math GS12" }];

export function SubjectSelector() {
  const [open, setOpen] = useState(false);
  const [value, setValue] = useState(SUBJECT_OPTIONS[0]);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onDoc = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, [open]);

  const ScaleIcon = Icons.scale;
  const ChevIcon = Icons.chevron;
  const CheckIcon = Icons.check;

  return (
    <div className="subj-sel" ref={ref}>
      <button
        type="button"
        className={`subj-trigger${open ? " is-open" : ""}`}
        aria-haspopup="listbox"
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
      >
        <span className="subj-ico"><ScaleIcon size={15} className="" /></span>
        <span className="subj-label">Subject</span>
        <span className="subj-value">{value.label}</span>
        <span className="subj-chev"><ChevIcon size={14} className="" /></span>
      </button>
      {open && (
        <div className="subj-menu" role="listbox">
          {SUBJECT_OPTIONS.map((opt) => (
            <button
              key={opt.id}
              type="button"
              role="option"
              aria-selected={opt.id === value.id}
              className={`subj-item${opt.id === value.id ? " is-active" : ""}`}
              onClick={() => { setValue(opt); setOpen(false); }}
            >
              <span>{opt.label}</span>
              {opt.id === value.id && <CheckIcon size={13} className="" />}
            </button>
          ))}
          <div className="subj-foot">More subjects coming soon</div>
        </div>
      )}
    </div>
  );
}
