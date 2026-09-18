// Account footer: the signed-in email (cached at login — there is no backend
// /me endpoint) with an initial avatar, the caller's run count, and sign out.
//
// The design's sub-line reads "Pro · 84 runs left"; this product has no plans
// or quotas, so the line shows the one true figure available here — how many
// runs the account has made.

import { useNavigate } from "react-router-dom";

import { useAuth } from "../../hooks/useAuth";
import { useSessions } from "../../hooks/useSessions";
import { ROUTE_LOGIN } from "../../routes";

const UNKNOWN_ACCOUNT_LABEL = "Account";
const UNKNOWN_ACCOUNT_INITIAL = "?";
const SIGN_OUT_LABEL = "Sign out";
const SINGULAR_RUN_COUNT = 1;
const FIRST_CHARACTER_INDEX = 0;

function accountInitial(email: string | null): string {
  if (email === null || email === "") {
    return UNKNOWN_ACCOUNT_INITIAL;
  }
  return email.charAt(FIRST_CHARACTER_INDEX);
}

function runCountLabel(runCount: number): string {
  return runCount === SINGULAR_RUN_COUNT ? "1 research run" : `${runCount} research runs`;
}

export function AccountFooter() {
  const { email, signOut } = useAuth();
  const navigate = useNavigate();
  const { data: sessions } = useSessions();

  function handleSignOut(): void {
    signOut();
    navigate(ROUTE_LOGIN);
  }

  return (
    <div className="account-footer">
      <div className="account-footer__row">
        <span className="account-footer__avatar" aria-hidden="true">
          {accountInitial(email)}
        </span>
        <span className="account-footer__identity">
          <span className="account-footer__email">{email ?? UNKNOWN_ACCOUNT_LABEL}</span>
          {sessions !== undefined && (
            <span className="account-footer__meta">{runCountLabel(sessions.length)}</span>
          )}
        </span>
        <button type="button" className="account-footer__sign-out" onClick={handleSignOut}>
          {SIGN_OUT_LABEL}
        </button>
      </div>
    </div>
  );
}
