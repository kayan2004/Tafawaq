/* icons.tsx — stroke icons (24x24), ported from the prototype's lib.jsx.
   Shared icon registry — not a single-component module, so fast-refresh's
   only-export-components rule does not apply here. */
/* eslint-disable react-refresh/only-export-components */
import type { CSSProperties, ReactNode } from "react";

export interface IconProps {
  size?: number;
  sw?: number;
  fill?: string;
  className?: string;
  style?: CSSProperties;
}

interface IcoProps extends IconProps {
  d?: string;
  paths?: ReactNode;
}

function Ico({ d, paths, fill, size = 20, sw = 2, className = "nav-ico", style }: IcoProps) {
  return (
    <svg
      className={className}
      style={style}
      viewBox="0 0 24 24"
      width={size}
      height={size}
      fill={fill || "none"}
      stroke={fill ? "none" : "currentColor"}
      strokeWidth={sw}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {paths ? paths : <path d={d} />}
    </svg>
  );
}

export type IconName =
  | "dashboard" | "exam" | "past" | "topics" | "chat" | "history"
  | "timer" | "check" | "arrow" | "chevron" | "send" | "spark"
  | "plus" | "alert" | "scale" | "target" | "flame" | "book" | "eye" | "eye-off";

export const Icons: Record<IconName, (p: IconProps) => ReactNode> = {
  dashboard: (p) => <Ico {...p} paths={<><rect x="3" y="3" width="7" height="9" rx="2"/><rect x="14" y="3" width="7" height="5" rx="2"/><rect x="14" y="12" width="7" height="9" rx="2"/><rect x="3" y="16" width="7" height="5" rx="2"/></>} />,
  exam: (p) => <Ico {...p} paths={<><path d="M8 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V5a2 2 0 0 0-2-2h-2"/><rect x="8" y="2" width="8" height="4" rx="1"/><path d="M9 12l2 2 4-4"/></>} />,
  past: (p) => <Ico {...p} paths={<><circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/><path d="M11 8v3l2 1.5"/></>} />,
  topics: (p) => <Ico {...p} paths={<><path d="M4 19V5"/><path d="M4 19h16"/><rect x="7" y="11" width="3" height="5" rx="1"/><rect x="12" y="7" width="3" height="9" rx="1"/><rect x="17" y="13" width="3" height="3" rx="1"/></>} />,
  chat: (p) => <Ico {...p} paths={<><path d="M21 15a2 2 0 0 1-2 2H8l-4 4V6a2 2 0 0 1 2-2h13a2 2 0 0 1 2 2z"/><path d="M8 10h8M8 13.5h5"/></>} />,
  history: (p) => <Ico {...p} paths={<><path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 4v4h4"/><path d="M12 8v4l3 2"/></>} />,
  timer: (p) => <Ico {...p} paths={<><circle cx="12" cy="13" r="8"/><path d="M12 13V9"/><path d="M9 2h6"/><path d="m19 6 1.5-1.5"/></>} />,
  check: (p) => <Ico {...p} paths={<path d="M20 6 9 17l-5-5"/>} />,
  arrow: (p) => <Ico {...p} paths={<path d="M5 12h14M13 6l6 6-6 6"/>} />,
  chevron: (p) => <Ico {...p} paths={<path d="m9 6 6 6-6 6"/>} />,
  send: (p) => <Ico {...p} paths={<path d="M14.5 9.5 4 13l6 2 2 6 3.5-10.5z M21 3l-7 6.5"/>} />,
  spark: (p) => <Ico {...p} paths={<><path d="M12 3v4M12 17v4M3 12h4M17 12h4"/><path d="m6 6 2.5 2.5M15.5 15.5 18 18M18 6l-2.5 2.5M8.5 15.5 6 18"/></>} />,
  plus: (p) => <Ico {...p} paths={<path d="M12 5v14M5 12h14"/>} />,
  alert: (p) => <Ico {...p} paths={<><path d="M12 9v4M12 17h.01"/><path d="M10.3 3.9 2 18a2 2 0 0 0 1.7 3h16.6a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/></>} />,
  scale: (p) => <Ico {...p} paths={<><path d="M12 3v18M7 7h10"/><path d="M7 7 4 14h6zM17 7l-3 7h6z"/><path d="M2 21h20" /></>} />,
  target: (p) => <Ico {...p} paths={<><circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="4"/><circle cx="12" cy="12" r="0.6" fill="currentColor" stroke="none"/></>} />,
  flame: (p) => <Ico {...p} paths={<path d="M12 3c1 3 4 4 4 8a4 4 0 0 1-8 0c0-1 .5-2 1-2.5C9 11 8 12 8 14a4 4 0 0 0 8 0c0-4-3-6-4-11z"/>} />,
  book: (p) => <Ico {...p} paths={<><path d="M4 5a2 2 0 0 1 2-2h13v16H6a2 2 0 0 0-2 2z"/><path d="M4 5v14"/></>} />,
  eye: (p) => <Ico {...p} paths={<><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7z"/><circle cx="12" cy="12" r="3"/></>} />,
  "eye-off": (p) => <Ico {...p} paths={<path d="M9.88 9.88a3 3 0 1 0 4.24 4.24M10.73 5.08A10.43 10.43 0 0 1 12 5c7 0 10 7 10 7a13.16 13.16 0 0 1-1.67 2.68M6.61 6.61A13.526 13.526 0 0 0 2 12s3 7 10 7a9.74 9.74 0 0 0 5.39-1.61M2 2l20 20"/>} />,
};
