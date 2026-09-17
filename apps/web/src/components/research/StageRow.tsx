// One row of the ProgressStepper. Pending rows are dimmed and collapsed;
// active rows auto-expand with a live, connected list of substep lines; done
// rows collapse to a single line with elapsed time (click to re-expand and
// review); an error row gets a distinct marker color, the plain-language
// failure message, and a "Try again" action.
//
// The active marker's pulse is a plain CSS animation — styles/research.css
// does not repeat the reduced-motion check itself, since styles/base.css
// already disables all animation-duration globally under
// `prefers-reduced-motion: reduce`.

import { formatElapsedDuration } from "../../lib/format";
import type { StageState } from "../../lib/researchEvents";

interface StageRowProps {
  label: string;
  state: StageState;
  isExpanded: boolean;
  onToggle: () => void;
  onRetry?: () => void;
  errorMessage?: string | null;
}

const TRY_AGAIN_LABEL = "Try again";

export function StageRow({
  label,
  state,
  isExpanded,
  onToggle,
  onRetry,
  errorMessage,
}: StageRowProps) {
  const isCollapsible = state.status === "done" || state.status === "active";
  const showSubsteps = isExpanded && state.substeps.length > 0;

  return (
    <li className={`stage-row stage-row--${state.status}`}>
      <button
        type="button"
        className="stage-row__header"
        onClick={isCollapsible ? onToggle : undefined}
        aria-expanded={isCollapsible ? isExpanded : undefined}
        disabled={!isCollapsible}
      >
        <span className="stage-row__marker" aria-hidden="true" />
        <span className="stage-row__label">{label}</span>
        {state.status === "done" && state.startedAt !== null && state.doneAt !== null && (
          <span className="stage-row__elapsed">
            {formatElapsedDuration(state.startedAt, state.doneAt)}
          </span>
        )}
      </button>

      {showSubsteps && (
        <ol className="stage-row__substeps">
          {state.substeps.map((substep, index) => (
            <li className="stage-row__substep" key={`${substep.at}-${index}`}>
              {substep.message}
            </li>
          ))}
        </ol>
      )}

      {state.status === "error" && (
        <div className="stage-row__error-actions">
          {errorMessage !== undefined && errorMessage !== null && errorMessage !== "" && (
            <p className="stage-row__error-message">{errorMessage}</p>
          )}
          {onRetry !== undefined && (
            <button type="button" className="stage-row__retry" onClick={onRetry}>
              {TRY_AGAIN_LABEL}
            </button>
          )}
        </div>
      )}
    </li>
  );
}
