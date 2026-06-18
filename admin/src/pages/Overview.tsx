import { useEffect, useState } from "react";
import { getOverview, type Overview as OverviewData } from "../lib/api";
import StatCard from "../components/StatCard";
import Skeleton from "../components/Skeleton";

export default function Overview({ token }: { token: string }) {
  const [data, setData] = useState<OverviewData | null>(null);

  useEffect(() => {
    void getOverview(token).then(setData);
  }, [token]);

  return (
    <div>
      <h1 className="text-[20px] font-extrabold tracking-[-0.02em]">Overview</h1>
      <p className="mt-1 text-[13px] font-medium" style={{ color: "var(--text-muted)" }}>
        Content and platform health for Lebanese GS Grade 12 Mathematics.
      </p>

      {!data ? (
        <div className="mt-5 grid grid-cols-4 gap-3.5">
          {Array.from({ length: 8 }).map((_, i) => (
            <Skeleton key={i} className="h-[90px]" />
          ))}
        </div>
      ) : (
        <div className="mt-5 grid grid-cols-4 gap-3.5">
          <StatCard
            label="Total users"
            value={data.total_users}
            sublabel={`${data.onboarded_users} onboarded (${Math.round(data.onboarding_rate * 100)}%)`}
          />
          <StatCard label="Exams generated" value={data.exams_generated} />
          <StatCard label="Exams submitted" value={data.exams_submitted} />
          <StatCard
            label="Past-exam files"
            value={`${data.past_exam_files_ingested}/${data.past_exam_files_total}`}
            sublabel="PDF files ingested"
          />
          <StatCard label="Chunks — past exams" value={data.chunks_by_source_type.past_exam ?? 0} />
          <StatCard label="Chunks — answer keys" value={data.chunks_by_source_type.answer_key ?? 0} />
          <StatCard
            label="Chunks — textbook"
            value={
              (data.chunks_by_source_type.textbook_theory ?? 0) +
              (data.chunks_by_source_type.textbook_exercise ?? 0) +
              (data.chunks_by_source_type.textbook_self_evaluation ?? 0)
            }
          />
          <StatCard label="Topics tracked" value={data.topics_tracked} />
          <StatCard
            label="Messages (7d)"
            value={data.messages_7d}
            sublabel={`${data.messages_total} total`}
          />
        </div>
      )}
    </div>
  );
}
