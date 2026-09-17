import { useState } from "react";
import type { FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";

import { DuplicateEmailError, SignupValidationError } from "../../api/auth";
import { MIN_PASSWORD_LENGTH } from "../../constants";
import { useAuth } from "../../hooks/useAuth";
import { ROUTE_HOME, ROUTE_LOGIN } from "../../routes";

const GENERIC_SIGNUP_FAILURE_MESSAGE =
  "Couldn't create your account. Try again in a moment.";
const DUPLICATE_EMAIL_MESSAGE = "An account with this email already exists.";
const PASSWORD_TOO_SHORT_MESSAGE = `Password must be at least ${MIN_PASSWORD_LENGTH} characters.`;
const PASSWORD_MISMATCH_MESSAGE = "Passwords do not match.";

export function SignupForm() {
  const { signUp } = useAuth();
  const navigate = useNavigate();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [passwordFieldError, setPasswordFieldError] = useState<string | null>(null);
  const [confirmFieldError, setConfirmFieldError] = useState<string | null>(null);
  const [isDuplicateEmail, setIsDuplicateEmail] = useState(false);
  const [bannerError, setBannerError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  function validate(): boolean {
    let isValid = true;

    if (password.length < MIN_PASSWORD_LENGTH) {
      setPasswordFieldError(PASSWORD_TOO_SHORT_MESSAGE);
      isValid = false;
    } else {
      setPasswordFieldError(null);
    }

    if (confirmPassword !== password) {
      setConfirmFieldError(PASSWORD_MISMATCH_MESSAGE);
      isValid = false;
    } else {
      setConfirmFieldError(null);
    }

    return isValid;
  }

  async function handleSubmit(event: FormEvent): Promise<void> {
    event.preventDefault();
    setBannerError(null);
    setIsDuplicateEmail(false);

    if (!validate()) {
      return;
    }

    setIsSubmitting(true);
    try {
      await signUp(email, password);
      navigate(ROUTE_HOME, { replace: true });
    } catch (signupError) {
      if (signupError instanceof DuplicateEmailError) {
        setIsDuplicateEmail(true);
      } else if (signupError instanceof SignupValidationError) {
        setPasswordFieldError(PASSWORD_TOO_SHORT_MESSAGE);
      } else {
        setBannerError(GENERIC_SIGNUP_FAILURE_MESSAGE);
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form className="auth-form" onSubmit={handleSubmit} noValidate>
      <h1 className="auth-form__title">Create account</h1>
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
          autoComplete="new-password"
          minLength={MIN_PASSWORD_LENGTH}
          aria-describedby={passwordFieldError !== null ? "signup-password-error" : undefined}
          aria-invalid={passwordFieldError !== null}
          required
        />
        {passwordFieldError !== null && (
          <span className="auth-form__field-error" id="signup-password-error" role="alert">
            {passwordFieldError}
          </span>
        )}
      </label>
      <label className="auth-form__field">
        <span className="auth-form__label">Confirm password</span>
        <input
          type="password"
          value={confirmPassword}
          onChange={(event) => setConfirmPassword(event.target.value)}
          autoComplete="new-password"
          aria-describedby={confirmFieldError !== null ? "signup-confirm-error" : undefined}
          aria-invalid={confirmFieldError !== null}
          required
        />
        {confirmFieldError !== null && (
          <span className="auth-form__field-error" id="signup-confirm-error" role="alert">
            {confirmFieldError}
          </span>
        )}
      </label>
      {isDuplicateEmail && (
        <p className="auth-form__banner-error" role="alert">
          {DUPLICATE_EMAIL_MESSAGE}{" "}
          <Link to={ROUTE_LOGIN} state={{ prefillEmail: email }}>
            Sign in instead
          </Link>
        </p>
      )}
      {bannerError !== null && (
        <p className="auth-form__banner-error" role="alert">
          {bannerError}
        </p>
      )}
      <button type="submit" className="auth-form__submit" disabled={isSubmitting}>
        {isSubmitting ? "Creating account…" : "Create account"}
      </button>
      <p className="auth-form__switch">
        Already have an account? <Link to={ROUTE_LOGIN}>Sign in</Link>
      </p>
    </form>
  );
}
