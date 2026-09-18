// One row of the research plan card: a circular mark (done / in flight /
// queued / failed), the step's title, and its meta line. A failed step also
// carries the failure message and the "Try again" action.

import { Check } from "lucide-react";

import { ICON_STROKE_WIDTH } from "../../constants";
import type { PlanStep } from "../../lib/planSteps";

const TRY_AGAIN_LABEL = "Try again";
const CHECK_ICON_SIZE = 10;
const ACTIVE_MARK_GLYPH = "•";
const ERROR_MARK_GLYPH = "!";

interface PlanStepRowProps {
  step: PlanStep;
  onRetry?: () => void;
  errorMessage?: string | null;
}

function StepMark({ status }: { status: PlanStep["state"]["status"] }) {
  if (status === "done") {
    return <Check size={CHECK_ICON_SIZE} strokeWidth={ICON_STROKE_WIDTH} aria-hidden="true" />;
  }
  if (status === "active") {
    return <span aria-hidden="true">{ACTIVE_MARK_GLYPH}</span>;
  }
  if (status === "error") {
    return <span aria-hidden="true">{ERROR_MARK_GLYPH}</span>;
  }
  return null;
}

export function PlanStepRow({ step, onRetry, errorMessage }: PlanStepRowProps) {
  return (
    <li className={`plan-step plan-step--${step.state.status}`}>
      <span className="plan-step__mark">
        <StepMark status={step.state.status} />
      </span>
      <div className="plan-step__body">
        <div className="plan-step__title">{step.label}</div>
        <div className="plan-step__meta">{step.meta}</div>
        {step.state.status === "error" && (
          <div className="plan-step__error">
            {errorMessage !== undefined && errorMessage !== null && errorMessage !== "" && (
              <p className="plan-step__error-message">{errorMessage}</p>
            )}
            {onRetry !== undefined && (
              <button type="button" className="plan-step__retry" onClick={onRetry}>
                {TRY_AGAIN_LABEL}
              </button>
            )}
          </div>
        )}
      </div>
    </li>
  );
}
