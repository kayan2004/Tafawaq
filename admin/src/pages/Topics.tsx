import { useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { getTopics, type TopicsResponse } from "../lib/api";
import { TierBadge } from "../components/Badge";
import Card from "../components/Card";
import EmptyState from "../components/EmptyState";
import { Icons } from "../lib/icons";

type SortKey = "topic" | "appearances" | "last_seen_year";
type SortDir = "asc" | "desc";

export default function Topics({ token }: { token: string }) {
  const [data, setData] = useState<TopicsResponse | null>(null);
  const [sortKey, setSortKey] = useState<SortKey>("appearances");
  const [sortDir, setSortDir] = useState<SortDir>("desc");

  useEffect(() => {
    void getTopics(token).then(setData);
  }, [token]);

  const sorted = useMemo(() => {
    if (!data) return [];
    const rows = [...data.topics];
    rows.sort((a, b) => {
      let cmp: number;
      if (sortKey === "topic") cmp = a.topic.localeCompare(b.topic);
      else if (sortKey === "appearances") cmp = a.appearances - b.appearances;
      else cmp = a.last_seen_year - b.last_seen_year;
      return sortDir === "asc" ? cmp : -cmp;
    });
    return rows;
  }, [data, sortKey, sortDir]);

  const maxAppearances = Math.max(1, ...sorted.map((t) => t.appearances));

  function toggleSort(key: SortKey) {
    if (key === sortKey) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("desc");
    }
  }

  function sortIndicator(key: SortKey) {
    if (key !== sortKey) return null;
    return sortDir === "asc" ? " ↑" : " ↓";
  }

  return (
    <div>
      <h1 className="text-[20px] font-extrabold tracking-[-0.02em]">Topic analytics</h1>
      <p className="mt-1 text-[13px] font-medium" style={{ color: "var(--text-muted)" }}>
        Curriculum topic frequency across ingested past exams.
      </p>

      <div
        className="mt-4 flex items-center gap-2 rounded-md border px-3.5 py-2.5"
        style={{ background: "var(--surface-2)", borderColor: "var(--line)" }}
      >
        <Icons.info size={15} style={{ color: "var(--text-muted)" }} />
        <span className="text-[12.5px]" style={{ color: "var(--text-2)" }}>
          Frequency is computed from ingested past-exam chunks only — it grows as more exam years are ingested.
        </span>
      </div>

      {data && sorted.length === 0 && (
        <Card className="mt-5">
          <EmptyState
            icon="analytics"
            heading="No topic data yet"
            body="Ingest past exams to populate topic frequency analytics."
          />
        </Card>
      )}

      {data && sorted.length > 0 && (
        <Card className="mt-5">
          <table className="w-full border-collapse">
            <thead>
              <tr>
                <Th onClick={() => toggleSort("topic")}>Topic{sortIndicator("topic")}</Th>
                <Th onClick={() => toggleSort("appearances")} align="right">
                  Appearances{sortIndicator("appearances")}
                </Th>
                <Th>Frequency</Th>
                <Th onClick={() => toggleSort("last_seen_year")} align="right">
                  Last seen{sortIndicator("last_seen_year")}
                </Th>
                <Th>Tier</Th>
              </tr>
            </thead>
            <tbody>
              {sorted.map((t) => (
                <tr key={t.topic}>
                  <Td>{t.topic}</Td>
                  <Td align="right" mono>{t.appearances}</Td>
                  <Td>
                    <div className="h-2 w-[100px] rounded-full" style={{ background: "var(--surface-3)" }}>
                      <div
                        className="h-2 rounded-full"
                        style={{
                          width: `${Math.max(6, (t.appearances / maxAppearances) * 100)}%`,
                          background:
                            t.frequency_tier === "high" ? "#3a4351" :
                            t.frequency_tier === "medium" ? "#6b7688" : "#c2cbd9",
                        }}
                      />
                    </div>
                  </Td>
                  <Td align="right" mono>{t.last_seen_year}</Td>
                  <Td><TierBadge tier={t.frequency_tier} /></Td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}

      {data && data.gaps.length > 0 && (
        <Card title="Coverage gaps" caption="Curriculum topics with zero exam appearances" className="mt-5">
          <div className="flex flex-wrap gap-2 p-4">
            {data.gaps.map((g) => (
              <span
                key={g}
                className="rounded-full border px-2.5 py-1 text-[12.5px]"
                style={{ background: "var(--surface-2)", borderColor: "var(--line)" }}
              >
                {g}
              </span>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}

function Th({ children, onClick, align }: { children: ReactNode; onClick?: () => void; align?: "right" }) {
  return (
    <th
      onClick={onClick}
      className={`px-4 py-2.5 text-[11px] font-bold uppercase tracking-[0.07em] ${onClick ? "cursor-pointer" : ""} ${align === "right" ? "text-right" : "text-left"}`}
      style={{ color: "var(--text-muted)", borderBottom: "1px solid var(--line)" }}
    >
      {children}
    </th>
  );
}

function Td({ children, align, mono }: { children: ReactNode; align?: "right"; mono?: boolean }) {
  return (
    <td
      className={`px-4 py-3 text-[13px] ${align === "right" ? "text-right" : "text-left"}`}
      style={{ borderTop: "1px solid var(--line)", fontFamily: mono ? "var(--font-mono)" : undefined }}
    >
      {children}
    </td>
  );
}
