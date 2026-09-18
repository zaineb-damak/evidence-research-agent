import { AuthSplitPanel } from "../components/auth/AuthSplitPanel";
import { SignupForm } from "../components/auth/SignupForm";

export function SignupPage() {
  return (
    <AuthSplitPanel>
      <SignupForm />
    </AuthSplitPanel>
  );
}
