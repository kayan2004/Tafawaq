import { Icons } from "../lib/icons";
import type { StepStatus } from "../lib/ingestionSteps";

interface ProgressStepsProps {
  steps: string[];
  statuses: StepStatus[];
}

export default function ProgressSteps({ steps, statuses }: ProgressStepsProps) {
  return (
    <div className="flex items-center">
      {steps.map((step, i) => {
        const status = statuses[i] ?? "pending";
        const color =
          status === "done" ? "#262d39" :
          status === "active" ? "#6b7688" :
          status === "failed" ? "var(--danger)" :
          "var(--surface-3)";
        const textColor = status === "pending" ? "var(--text-faint)" : "var(--text)";
        return (
          <div key={step} className="flex items-center">
            <div className="flex flex-col items-center gap-1">
              <span
                className="flex h-5 w-5 items-center justify-center rounded-full text-[10px] font-bold"
                style={{ background: color, color: status === "pending" ? "var(--text-faint)" : "#fff" }}
              >
                {status === "done" ? <Icons.check size={11} sw={3} /> : i + 1}
              </span>
              <span className="text-[10.5px] font-semibold whitespace-nowrap" style={{ color: textColor }}>
                {step}
              </span>
            </div>
            {i < steps.length - 1 && (
              <span className="mx-1.5 mb-3.5 h-px w-5" style={{ background: "var(--line-strong)" }} />
            )}
          </div>
        );
      })}
    </div>
  );
}
