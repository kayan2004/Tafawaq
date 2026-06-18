interface TabsProps {
  tabs: string[];
  active: string;
  onChange: (tab: string) => void;
}

export default function Tabs({ tabs, active, onChange }: TabsProps) {
  return (
    <div className="flex gap-1 border-b" style={{ borderColor: "var(--line)" }}>
      {tabs.map((tab) => {
        const isActive = tab === active;
        return (
          <button
            key={tab}
            onClick={() => onChange(tab)}
            className="px-3 py-2 text-[13px] font-bold -mb-px border-b-2 transition-colors"
            style={{
              color: isActive ? "var(--text)" : "var(--text-muted)",
              borderColor: isActive ? "var(--text)" : "transparent",
            }}
          >
            {tab}
          </button>
        );
      })}
    </div>
  );
}
