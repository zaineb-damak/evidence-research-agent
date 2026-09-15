import { PIPELINE_STEPS } from "../constants";
import type { ResearchJobSummary, ResearchStatus } from "../api/types";

const COMPLETED_STATUS: ResearchStatus = "completed";
const FAILED_STATUS: ResearchStatus = "failed";

// Rank of each status in the pipeline, used to mark steps done/active/pending.
const STATUS_ORDER: ResearchStatus[] = [
  "queued",
  "planning",
  "searching",
  "extracting",
  "resolving",
  "verifying",
  "synthesizing",
  "completed",
];

function statusRank(status: ResearchStatus): number {
  const index = STATUS_ORDER.indexOf(status);
  return index === -1 ? 0 : index;
}

interface ProgressViewProps {
  summary: ResearchJobSummary;
}

export function ProgressView({ summary }: ProgressViewProps) {
  const currentRank = statusRank(summary.status);

  if (summary.status === FAILED_STATUS) {
    return <p className="error">Research failed: {summary.error}</p>;
  }

  return (
    <div className="progress">
      <ul>
        {PIPELINE_STEPS.map((step) => {
          const stepRank = statusRank(step.status as ResearchStatus);
          const isDone =
            summary.status === COMPLETED_STATUS || stepRank < currentRank;
          const isActive = stepRank === currentRank;
          const marker = isDone ? "✓" : isActive ? "●" : "○";
          return (
            <li key={step.status} className={isActive ? "active" : ""}>
              {marker} {step.label}
            </li>
          );
        })}
      </ul>
      <p className="counts">
        {summary.counts.sources} sources · {summary.counts.claims} claims ·{" "}
        {summary.counts.contradictions} contradictions · $
        {summary.cost.usd.toFixed(4)}
      </p>
    </div>
  );
}
