// Two-column authenticated layout: a fixed-width sidebar, a header row
// hosting the account menu, and the routed page content. Wired as a layout
// route in routes.tsx around the authenticated pages (login/signup render
// outside this shell).

import { Outlet } from "react-router-dom";

import { AccountMenu } from "./AccountMenu";
import { Sidebar } from "./Sidebar";

export function AppShell() {
  return (
    <div className="app-shell">
      <Sidebar />
      <div className="app-shell__content">
        <header className="app-shell__header">
          <AccountMenu />
        </header>
        <main className="app-shell__main">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
