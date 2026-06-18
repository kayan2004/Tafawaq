export type StepStatus = "done" | "active" | "failed" | "pending";

/** Derives a per-step status array from the last-known stage name reported by SSE. */
export function computeStepStatuses(stages: string[], currentStage: string | undefined, failed: boolean): StepStatus[] {
  if (!currentStage) return stages.map(() => "pending");
  const idx = stages.findIndex((s) => s.toLowerCase() === currentStage.toLowerCase());
  if (idx === -1) return stages.map(() => "pending");
  return stages.map((_, i) => {
    if (i < idx) return "done";
    if (i === idx) return failed ? "failed" : "active";
    return "pending";
  });
}
