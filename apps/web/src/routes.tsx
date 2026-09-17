// Route table for the app. Path constants live here so no other module
// hard-codes a route string (CLAUDE.md: no magic values).

import { Route, Routes } from "react-router-dom";

import { RequireAuth } from "./components/auth/RequireAuth";
import { AppShell } from "./components/shell/AppShell";
import { HomePage } from "./pages/HomePage";
import { LoginPage } from "./pages/LoginPage";
import { NotFoundPage } from "./pages/NotFoundPage";
import { ResearchPage } from "./pages/ResearchPage";
import { SignupPage } from "./pages/SignupPage";

export const ROUTE_LOGIN = "/login";
export const ROUTE_SIGNUP = "/signup";
export const ROUTE_HOME = "/";
export const ROUTE_RESEARCH = "/research/:researchId";
export const ROUTE_NOT_FOUND = "*";

const RESEARCH_ID_ROUTE_PARAM = ":researchId";

// Builds a concrete /research/:researchId link from the route pattern above,
// so a literal "/research/" prefix isn't duplicated in every caller (e.g.
// components/shell/SessionListItem.tsx).
export function buildResearchPath(researchId: string): string {
  return ROUTE_RESEARCH.replace(RESEARCH_ID_ROUTE_PARAM, researchId);
}

export function AppRoutes() {
  return (
    <Routes>
      <Route path={ROUTE_LOGIN} element={<LoginPage />} />
      <Route path={ROUTE_SIGNUP} element={<SignupPage />} />
      <Route
        element={
          <RequireAuth>
            <AppShell />
          </RequireAuth>
        }
      >
        <Route path={ROUTE_HOME} element={<HomePage />} />
        <Route path={ROUTE_RESEARCH} element={<ResearchPage />} />
      </Route>
      <Route path={ROUTE_NOT_FOUND} element={<NotFoundPage />} />
    </Routes>
  );
}
