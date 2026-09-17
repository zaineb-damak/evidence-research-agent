// Adapted from the pre-router components/LoginForm.tsx: same submit logic
// (now calling useAuth().signIn instead of api/auth.login directly, so the
// rest of the app sees reactive auth state), restyled onto styles/auth.css,
// and now navigates itself instead of taking an onAuthenticated callback —
// back to the route the user originally tried to reach (see RequireAuth), or
// home. It also prefills the email when arriving from the signup page's
// "an account with this email already exists" link.

import { useState } from "react";
import type { FormEvent } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";

import { useAuth } from "../../hooks/useAuth";
import { ROUTE_HOME, ROUTE_SIGNUP } from "../../routes";

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
      setError(signInError instanceof Error ? signInError.message : "Sign in failed");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form className="auth-form" onSubmit={handleSubmit} noValidate>
      <h1 className="auth-form__title">Sign in</h1>
      <label className="auth-form__field">
        <span className="auth-form__label">Email</span>
        <input
          type="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          autoComplete="email"
          required
        />
      </label>
      <label className="auth-form__field">
        <span className="auth-form__label">Password</span>
        <input
          type="password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
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
        {isSubmitting ? "Signing in…" : "Sign in"}
      </button>
      <p className="auth-form__switch">
        Don&apos;t have an account? <Link to={ROUTE_SIGNUP}>Create one</Link>
      </p>
    </form>
  );
}
