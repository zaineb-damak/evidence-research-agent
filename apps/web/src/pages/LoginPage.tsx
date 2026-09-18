import { AuthSplitPanel } from "../components/auth/AuthSplitPanel";
import { LoginForm } from "../components/auth/LoginForm";

export function LoginPage() {
  return (
    <AuthSplitPanel>
      <LoginForm />
    </AuthSplitPanel>
  );
}
