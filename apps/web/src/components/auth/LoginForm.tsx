// Sign-in form. Calls useAuth().signIn (so the rest of the app sees reactive
// auth state) and navigates back to the route the user originally tried to
// reach (see RequireAuth), or home. The email is prefilled when arriving
// from the signup page's "an account with this email already exists" link.
//
// The handoff's OAuth buttons and "Forgot?" link are left out: there is no
// OAuth provider and no password-reset flow behind them yet.

import { useState } from "react";
import type { FormEvent } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";

import { BRAND_NAME } from "../../constants";
import { useAuth } from "../../hooks/useAuth";
import { ROUTE_HOME, ROUTE_SIGNUP } from "../../routes";

const TITLE = "Welcome back";
const SUBTITLE = "Sign in to pick up your research history.";
const EMAIL_LABEL = "Email";
const EMAIL_PLACEHOLDER = "you@company.com";
const PASSWORD_LABEL = "Password";
const PASSWORD_PLACEHOLDER = "••••••••";
const SUBMIT_LABEL = "Sign in";
const SUBMITTING_LABEL = "Signing in…";
const SWITCH_PROMPT = `New to ${BRAND_NAME}?`;
const SWITCH_CTA = "Create an account";
const GENERIC_FAILURE_MESSAGE = "Sign in failed";

interface LoginLocationState {
  from?: { pathname: string };
  prefillEmail?: string;
}

export function LoginForm() {
  const { signIn } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const locationState = (location.state as LoginLocationState | null) ?? {};

  const [email, setEmail] = useState(locationState.prefillEmail ?? "");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent): Promise<void> {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      await signIn(email, password);
      navigate(locationState.from?.pathname ?? ROUTE_HOME, { replace: true });
    } catch (signInError) {
      setError(signInError instanceof Error ? signInError.message : GENERIC_FAILURE_MESSAGE);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form className="auth-form" onSubmit={handleSubmit} noValidate>
      <h1 className="auth-form__title">{TITLE}</h1>
      <p className="auth-form__subtitle">{SUBTITLE}</p>

      <div className="auth-form__fields">
        <label className="auth-form__field">
          <span className="auth-form__label">{EMAIL_LABEL}</span>
          <input
            className="auth-form__input"
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            placeholder={EMAIL_PLACEHOLDER}
            autoComplete="email"
            required
          />
        </label>
        <label className="auth-form__field">
          <span className="auth-form__label">{PASSWORD_LABEL}</span>
          <input
            className="auth-form__input"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            placeholder={PASSWORD_PLACEHOLDER}
            autoComplete="current-password"
            required
          />
        </label>

        {error !== null && (
          <p className="auth-form__banner-error" role="alert">
            {error}
          </p>
        )}

        <button type="submit" className="auth-form__submit" disabled={isSubmitting}>
          {isSubmitting ? SUBMITTING_LABEL : SUBMIT_LABEL}
        </button>
      </div>

      <p className="auth-form__switch">
        {SWITCH_PROMPT} <Link to={ROUTE_SIGNUP}>{SWITCH_CTA}</Link>
      </p>
    </form>
  );
}
