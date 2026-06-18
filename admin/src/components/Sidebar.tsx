import { Icons, type IconName } from "../lib/icons";
import Logo from "./Logo";

export type Section = "overview" | "ingestion" | "topics" | "guardrails" | "users";

const NAV_ITEMS: { id: Section; label: string; icon: IconName }[] = [
  { id: "overview", label: "Overview", icon: "overview" },
  { id: "ingestion", label: "Ingestion", icon: "ingestion" },
  { id: "topics", label: "Topics", icon: "analytics" },
  { id: "guardrails", label: "Guardrails", icon: "shield" },
  { id: "users", label: "Users", icon: "users" },
];

interface SidebarProps {
  active: Section;
  onNavigate: (section: Section) => void;
  email: string;
  theme: "light" | "dark";
  onToggleTheme: () => void;
}

export default function Sidebar({ active, onNavigate, email, theme, onToggleTheme }: SidebarProps) {
  const logoColor = theme === "dark" ? "#ffffff" : "#0e1218";

  return (
    <div
      className="fixed left-0 top-0 z-40 flex h-full w-[220px] flex-col"
      style={{ background: "var(--surface)", borderRight: "1px solid var(--line)", padding: "16px 12px 20px" }}
    >
      <div className="flex items-start justify-between gap-2 pb-6">
        <div className="flex flex-col gap-1">
          <Logo color={logoColor} width={116} />
          <div className="text-[10px] font-bold uppercase tracking-[0.08em]" style={{ color: "var(--text-faint)" }}>
            Admin · Ops
          </div>
        </div>
        <button
          onClick={onToggleTheme}
          aria-label="Toggle theme"
          className="flex h-[30px] w-[30px] shrink-0 items-center justify-center rounded-md border"
          style={{ borderColor: "var(--line-strong)", color: "var(--text-2)" }}
        >
          {theme === "dark" ? <Icons.sun size={15} /> : <Icons.moon size={15} />}
        </button>
      </div>

      <nav className="flex flex-1 flex-col gap-0.5">
        {NAV_ITEMS.map((item) => {
          const isActive = item.id === active;
          const Icon = Icons[item.icon];
          return (
            <button
              key={item.id}
              onClick={() => onNavigate(item.id)}
              className="flex items-center gap-2.5 rounded-md px-2.5 py-2 text-left text-[13px]"
              style={{
                background: isActive ? "var(--surface-3)" : "transparent",
                color: isActive ? "var(--text)" : "var(--text-muted)",
                fontWeight: isActive ? 700 : 600,
              }}
            >
              <Icon size={17} />
              {item.label}
            </button>
          );
        })}
      </nav>

      <div
        className="flex flex-col gap-0.5 overflow-hidden rounded-md px-2.5 py-2"
        style={{ background: "var(--surface-2)" }}
      >
        <div className="truncate text-[12px] font-bold" style={{ color: "var(--text)" }}>
          Admin
        </div>
        <div className="truncate text-[10.5px]" style={{ color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
          {email}
        </div>
      </div>
    </div>
  );
}
