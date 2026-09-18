// Shared layout for /login and /signup: the form on the left, a value pane
// on the right stating what the product actually does. Both panes share a
// flex basis so they stack on narrow viewports.

import type { ReactNode } from "react";

import { BRAND_NAME } from "../../constants";

const VALUE_EYEBROW = `Why ${BRAND_NAME}`;
const VALUE_QUOTE =
  "Every answer arrives with its plan, its sources, and the reasoning it used to get there.";

// The handoff's third bullet promises editing a plan mid-run, which the
// pipeline doesn't support; it reads as "follow" here instead.
const VALUE_POINTS = [
  "Agent-written plans you can follow step by step as the run happens.",
  "Every claim links back to the passage it came from.",
  "Pick your sources: web, docs, papers, arXiv, GitHub, Reddit.",
];

interface AuthSplitPanelProps {
  children: ReactNode;
}

export function AuthSplitPanel({ children }: AuthSplitPanelProps) {
  return (
    <div className="auth-split">
      <div className="auth-split__form-pane">
        <div className="auth-split__form">
          <div className="brand auth-split__brand">
            <span className="brand__mark" aria-hidden="true" />
            <span className="brand__name">{BRAND_NAME}</span>
          </div>
          {children}
        </div>
      </div>

      <div className="auth-split__value-pane">
        <div className="auth-split__value">
          <p className="eyebrow auth-split__value-eyebrow">{VALUE_EYEBROW}</p>
          <p className="auth-split__quote">{VALUE_QUOTE}</p>
          <ul className="auth-split__points">
            {VALUE_POINTS.map((point) => (
              <li className="auth-split__point" key={point}>
                <span className="auth-split__point-dot" aria-hidden="true" />
                <span>{point}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
