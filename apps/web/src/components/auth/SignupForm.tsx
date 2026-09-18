// Account creation. Matches the handoff's single-password form (no confirm
// field), with the backend's minimum length enforced inline before submit.
// The handoff's Name field and OAuth buttons are left out: POST /auth/signup
// takes only an email and a password, and there is no OAuth provider.

import { useState } from "react";
import type { FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";

import { DuplicateEmailError, SignupValidationError } from "../../api/auth";
import { MIN_PASSWORD_LENGTH } from "../../constants";
import { useAuth } from "../../hooks/useAuth";
import { ROUTE_HOME, ROUTE_LOGIN } from "../../routes";

const TITLE = "Create your account";
// The handoff's "Ten free research runs a month" is a plan this product
// doesn't have; the line states what signing up actually gets you.
const SUBTITLE = "Your research history stays with your account.";
const EMAIL_LABEL = "Email";
const EMAIL_PLACEHOLDER = "you@company.com";
const PASSWORD_LABEL = "Password";
const PASSWORD_PLACEHOLDER = `At least ${MIN_PASSWORD_LENGTH} characters`;
const SUBMIT_LABEL = "Create account";
const SUBMITTING_LABEL = "Creating account…";
const SWITCH_PROMPT = "Already have an account?";
const SWITCH_CTA = "Sign in";
const SIGN_IN_INSTEAD_CTA = "Sign in instead";
const PASSWORD_ERROR_ID = "signup-password-error";

const GENERIC_SIGNUP_FAILURE_MESSAGE = "Couldn't create your account. Try again in a moment.";
const DUPLICATE_EMAIL_MESSAGE = "An account with this email already exists.";
const PASSWORD_TOO_SHORT_MESSAGE = `Password must be at least ${MIN_PASSWORD_LENGTH} characters.`;

export function SignupForm() {
  const { signUp } = useAuth();
  const navigate = useNavigate();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [passwordFieldError, setPasswordFieldError] = useState<string | null>(null);
  const [isDuplicateEmail, setIsDuplicateEmail] = useState(false);
  const [bannerError, setBannerError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  function validate(): boolean {
    if (password.length < MIN_PASSWORD_LENGTH) {
      setPasswordFieldError(PASSWORD_TOO_SHORT_MESSAGE);
      return false;
    }
    setPasswordFieldError(null);
    return true;
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
            autoComplete="new-password"
            minLength={MIN_PASSWORD_LENGTH}
            aria-describedby={passwordFieldError !== null ? PASSWORD_ERROR_ID : undefined}
            aria-invalid={passwordFieldError !== null}
            required
          />
          {passwordFieldError !== null && (
            <span className="auth-form__field-error" id={PASSWORD_ERROR_ID} role="alert">
              {passwordFieldError}
            </span>
          )}
        </label>

        {isDuplicateEmail && (
          <p className="auth-form__banner-error" role="alert">
            {DUPLICATE_EMAIL_MESSAGE}{" "}
            <Link to={ROUTE_LOGIN} state={{ prefillEmail: email }}>
              {SIGN_IN_INSTEAD_CTA}
            </Link>
          </p>
        )}
        {bannerError !== null && (
          <p className="auth-form__banner-error" role="alert">
            {bannerError}
          </p>
        )}

        <button type="submit" className="auth-form__submit" disabled={isSubmitting}>
          {isSubmitting ? SUBMITTING_LABEL : SUBMIT_LABEL}
        </button>
      </div>

      <p className="auth-form__switch">
        {SWITCH_PROMPT} <Link to={ROUTE_LOGIN}>{SWITCH_CTA}</Link>
      </p>
    </form>
  );
}
