import { AuthSplitPanel } from "../components/auth/AuthSplitPanel";
import { SignupForm } from "../components/auth/SignupForm";

const SIGNUP_STATEMENT =
  "Every claim traces back to a source. This tool plans, searches, and verifies before it writes a word.";

export function SignupPage() {
  return (
    <AuthSplitPanel statement={SIGNUP_STATEMENT}>
      <SignupForm />
    </AuthSplitPanel>
  );
}
