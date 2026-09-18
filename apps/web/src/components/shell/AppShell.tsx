// The persistent frame for all research work: a fixed-width sidebar beside
// the main column. Each page renders its own MainHeader (the header's title
// and status pill are page state), so this layout only owns the two columns
// and the sidebar's drawer state.

import { Outlet } from "react-router-dom";

import { SidebarProvider } from "../../context/SidebarContext";
import { Sidebar } from "./Sidebar";

export function AppShell() {
  return (
    <SidebarProvider>
      <div className="app-shell">
        <Sidebar />
        <div className="app-shell__main">
          <Outlet />
        </div>
      </div>
    </SidebarProvider>
  );
}
