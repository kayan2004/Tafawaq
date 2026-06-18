/* icons.tsx — minimal stroke icon registry (24x24), no external icon library. */
/* eslint-disable react-refresh/only-export-components */
import type { CSSProperties, ReactNode } from "react";

export interface IconProps {
  size?: number;
  sw?: number;
  className?: string;
  style?: CSSProperties;
}

interface IcoProps extends IconProps {
  paths: ReactNode;
}

function Ico({ paths, size = 17, sw = 2, className, style }: IcoProps) {
  return (
    <svg
      className={className}
      style={style}
      viewBox="0 0 24 24"
      width={size}
      height={size}
      fill="none"
      stroke="currentColor"
      strokeWidth={sw}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {paths}
    </svg>
  );
}

export type IconName =
  | "overview" | "ingestion" | "analytics" | "shield" | "users"
  | "chevronDown" | "chevronUp" | "sun" | "moon" | "book" | "file" | "fileText"
  | "play" | "upload" | "refresh" | "close" | "info" | "eye" | "alert"
  | "alertCircle" | "unlink" | "check" | "spark" | "search";

export const Icons: Record<IconName, (p: IconProps) => ReactNode> = {
  overview: (p) => <Ico {...p} paths={<><rect x="3" y="3" width="7" height="9" rx="1.5" /><rect x="14" y="3" width="7" height="5" rx="1.5" /><rect x="14" y="12" width="7" height="9" rx="1.5" /><rect x="3" y="16" width="7" height="5" rx="1.5" /></>} />,
  ingestion: (p) => <Ico {...p} paths={<><path d="M12 3v12" /><path d="m7 11 5 5 5-5" /><path d="M5 19h14" /></>} />,
  analytics: (p) => <Ico {...p} paths={<><path d="M4 19V5" /><path d="M4 19h16" /><rect x="7" y="11" width="3" height="5" rx="1" /><rect x="12" y="7" width="3" height="9" rx="1" /><rect x="17" y="13" width="3" height="3" rx="1" /></>} />,
  shield: (p) => <Ico {...p} paths={<path d="M12 3l8 3v6c0 4.5-3.4 7.5-8 9-4.6-1.5-8-4.5-8-9V6z" />} />,
  users: (p) => <Ico {...p} paths={<><circle cx="9" cy="8" r="3.2" /><path d="M3 20c0-3.3 2.7-6 6-6s6 2.7 6 6" /><path d="M16 5.2a3.2 3.2 0 0 1 0 6.2" /><path d="M21 20c0-2.6-1.7-4.8-4-5.7" /></>} />,
  chevronDown: (p) => <Ico {...p} paths={<path d="m6 9 6 6 6-6" />} />,
  chevronUp: (p) => <Ico {...p} paths={<path d="m18 15-6-6-6 6" />} />,
  sun: (p) => <Ico {...p} paths={<><circle cx="12" cy="12" r="4.2" /><path d="M12 2.5v2.5M12 19v2.5M4.2 4.2l1.8 1.8M18 18l1.8 1.8M2.5 12H5M19 12h2.5M4.2 19.8 6 18M18 6l1.8-1.8" /></>} />,
  moon: (p) => <Ico {...p} paths={<path d="M20 14.5A8.5 8.5 0 1 1 9.5 4a7 7 0 0 0 10.5 10.5z" />} />,
  book: (p) => <Ico {...p} paths={<><path d="M4 19.5V5.2C4 4 5 3.3 6.1 3.6 8 4 10 4.8 12 6c2-1.2 4-2 5.9-2.4C19 3.3 20 4 20 5.2v14.3" /><path d="M4 19.5c0-.9.8-1.5 1.7-1.5H10c.8 0 1.5.3 2 .8.5-.5 1.2-.8 2-.8h4.3c.9 0 1.7.6 1.7 1.5" /></>} />,
  file: (p) => <Ico {...p} paths={<><path d="M7 3h7l4 4v13a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1z" /><path d="M14 3v4h4" /></>} />,
  fileText: (p) => <Ico {...p} paths={<><path d="M7 3h7l4 4v13a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1z" /><path d="M14 3v4h4" /><path d="M9 13h6M9 17h6" /></>} />,
  play: (p) => <Ico {...p} paths={<path d="M7 4.5v15l13-7.5z" />} />,
  upload: (p) => <Ico {...p} paths={<><path d="M12 16V4M8 8l4-4 4 4" /><path d="M4 16v3a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-3" /></>} />,
  refresh: (p) => <Ico {...p} paths={<><path d="M3 11a9 9 0 0 1 15-6.7L21 7" /><path d="M21 3v4h-4" /><path d="M21 13a9 9 0 0 1-15 6.7L3 17" /><path d="M3 21v-4h4" /></>} />,
  close: (p) => <Ico {...p} paths={<path d="M6 6l12 12M18 6 6 18" />} />,
  info: (p) => <Ico {...p} paths={<><circle cx="12" cy="12" r="9" /><path d="M12 11v5M12 8h.01" /></>} />,
  eye: (p) => <Ico {...p} paths={<><path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12z" /><circle cx="12" cy="12" r="2.7" /></>} />,
  alert: (p) => <Ico {...p} paths={<><path d="M12 9v4M12 17h.01" /><path d="M10.3 3.9 2 18a2 2 0 0 0 1.7 3h16.6a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z" /></>} />,
  alertCircle: (p) => <Ico {...p} paths={<><circle cx="12" cy="12" r="9" /><path d="M12 8v5M12 16h.01" /></>} />,
  unlink: (p) => <Ico {...p} paths={<><path d="M9 15l6-6M9 9 7.5 7.5a3.5 3.5 0 0 0 0 5l.5.5M15 15l.5.5a3.5 3.5 0 0 0 5-5L19.5 9" /><path d="M3 3l18 18" /></>} />,
  check: (p) => <Ico {...p} paths={<path d="M20 6 9 17l-5-5" />} />,
  spark: (p) => <Ico {...p} paths={<><path d="M12 3v4M12 17v4M3 12h4M17 12h4" /><path d="m6 6 2.5 2.5M15.5 15.5 18 18M18 6l-2.5 2.5M8.5 15.5 6 18" /></>} />,
  search: (p) => <Ico {...p} paths={<><circle cx="11" cy="11" r="7" /><path d="m21 21-4.3-4.3" /></>} />,
};
