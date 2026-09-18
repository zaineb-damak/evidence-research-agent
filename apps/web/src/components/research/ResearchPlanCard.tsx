// The research plan: the agent's five steps with their live state. Replaces
// the old ProgressStepper — same stream state, the design's card treatment.
// The header dot pulses only while the run is still in flight.

import { buildPlanSteps, countCompletedSteps, PLAN_STEP_COUNT } from "../../lib/planSteps";
import type { ResearchStreamState } from "../../lib/researchEvents";
import { PlanStepRow } from "./PlanStepRow";

const CARD_TITLE = "Research plan";

interface ResearchPlanCardProps {
  streamState: ResearchStreamState;
  isRunning: boolean;
  onRetry: () => void;
}

export function ResearchPlanCard({ streamState, isRunning, onRetry }: ResearchPlanCardProps) {
  const steps = buildPlanSteps(streamState);
  const completedCount = countCompletedSteps(steps);

  return (
    <section className="plan-card">
      <header className="plan-card__header">
        <h2 className="plan-card__title">
          <span
            className={`plan-card__dot${isRunning ? " plan-card__dot--running" : ""}`}
            aria-hidden="true"
          />
          {CARD_TITLE}
        </h2>
        <span className="plan-card__progress">
          {completedCount} of {PLAN_STEP_COUNT} steps done
        </span>
      </header>
      <ol className="plan-card__steps">
        {steps.map((step) => (
          <PlanStepRow
            key={step.key}
            step={step}
            onRetry={step.state.status === "error" ? onRetry : undefined}
            errorMessage={step.state.status === "error" ? streamState.error : undefined}
          />
        ))}
      </ol>
    </section>
  );
}
