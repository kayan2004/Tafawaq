import { Icons } from "../lib/icons";
import { computeStepStatuses } from "../lib/ingestionSteps";
import { StatusBadge } from "./Badge";
import ProgressSteps from "./ProgressSteps";

export interface FileJob {
  filename: string;
  stage: string; // "pending" | "extract" | "parse" | "chunk" | "tag" | "embed" | "done"
  failed: boolean;
  error?: string;
  chunks?: number;
  pages?: number;
}

interface JobPanelProps {
  open: boolean;
  stageLabels: string[];
  jobs: FileJob[];
  onClose: () => void;
}

export default function JobPanel({ open, stageLabels, jobs, onClose }: JobPanelProps) {
  if (!open) return null;
  const doneCount = jobs.filter((j) => j.stage === "done").length;
  const failedCount = jobs.filter((j) => j.failed).length;
  const runningCount = jobs.length - doneCount - failedCount;

  return (
    <>
      <div className="fixed inset-0 z-[59]" style={{ background: "var(--overlay)" }} onClick={onClose} />
      <div
        className="tfw-slide-in fixed right-0 top-0 z-[60] h-full w-[480px] max-w-[92vw] overflow-y-auto"
        style={{ background: "var(--surface)", borderLeft: "1px solid var(--line)", boxShadow: "var(--shadow-lg)" }}
      >
        <div className="flex items-center justify-between border-b px-5 py-4" style={{ borderColor: "var(--line)" }}>
          <div>
            <div className="text-[15px] font-bold">Ingestion job</div>
            <div className="text-[12px]" style={{ color: "var(--text-muted)" }}>
              {jobs.length} files · {doneCount} done · {runningCount} running
              {failedCount > 0 ? ` · ${failedCount} failed` : ""}
            </div>
          </div>
          <button onClick={onClose} aria-label="Close">
            <Icons.close size={18} />
          </button>
        </div>
        <div className="flex flex-col gap-3 p-5">
          {jobs.map((job) => (
            <div key={job.filename} className="rounded-md border p-3" style={{ borderColor: "var(--line)" }}>
              <div className="flex items-center justify-between gap-2">
                <span className="truncate text-[12.5px]" style={{ fontFamily: "var(--font-mono)" }}>
                  {job.filename}
                </span>
                {job.failed ? (
                  <StatusBadge status="failed" />
                ) : job.stage === "done" ? (
                  <StatusBadge status="ingested" />
                ) : (
                  <StatusBadge status="processing" />
                )}
              </div>
              <div className="mt-3">
                <ProgressSteps steps={stageLabels} statuses={computeStepStatuses(stageLabels, job.stage, job.failed)} />
              </div>
              {job.failed && job.error && (
                <div
                  className="mt-3 rounded-md border p-2 text-[12px]"
                  style={{ background: "var(--danger-bg)", borderColor: "var(--danger-line)", color: "var(--on-danger)" }}
                >
                  {job.error}
                </div>
              )}
              {job.stage === "done" && job.chunks !== undefined && (
                <div className="mt-2 text-[11.5px]" style={{ color: "var(--text-muted)" }}>
                  {job.chunks} chunks{job.pages !== undefined ? ` · ${job.pages} pages` : ""}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </>
  );
}
