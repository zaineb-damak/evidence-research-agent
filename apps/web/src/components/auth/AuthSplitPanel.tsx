// Shared shell for /login and /signup: a left panel stating the product's
// actual mechanism (grounded, not marketing copy) and a right panel hosting
// the form itself.

import type { ReactNode } from "react";

interface AuthSplitPanelProps {
  statement: string;
  children: ReactNode;
}

export function AuthSplitPanel({ statement, children }: AuthSplitPanelProps) {
  return (
    <div className="auth-split">
      <div className="auth-split__statement-panel">
        <p className="auth-split__statement">{statement}</p>
      </div>
      <div className="auth-split__form-panel">{children}</div>
    </div>
  );
}
