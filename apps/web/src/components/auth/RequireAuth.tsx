// Route guard: redirects to /login when not authenticated, preserving the
// attempted destination in router state so LoginForm can navigate back
// there after a successful sign-in.

import { Navigate, useLocation } from "react-router-dom";
import type { ReactNode } from "react";

import { useAuth } from "../../hooks/useAuth";
import { ROUTE_LOGIN } from "../../routes";

interface RequireAuthProps {
  children: ReactNode;
}

export function RequireAuth({ children }: RequireAuthProps) {
  const { isAuthenticated } = useAuth();
  const location = useLocation();

  if (!isAuthenticated) {
    return <Navigate to={ROUTE_LOGIN} replace state={{ from: location }} />;
  }

  return <>{children}</>;
}
