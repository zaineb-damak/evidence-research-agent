import { AuthSplitPanel } from "../components/auth/AuthSplitPanel";
import { LoginForm } from "../components/auth/LoginForm";

const LOGIN_STATEMENT =
  "Every claim in this report traces back to a source passage. Sign in to pick up your research.";

export function LoginPage() {
  return (
    <AuthSplitPanel statement={LOGIN_STATEMENT}>
      <LoginForm />
    </AuthSplitPanel>
  );
}
