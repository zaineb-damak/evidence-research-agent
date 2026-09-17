// Sidebar: a link to start a new research run plus the real session-history
// list (GET /api/research via useSessions/SessionList).

import { Link } from "react-router-dom";

import { ROUTE_HOME } from "../../routes";
import { SessionList } from "./SessionList";

export function Sidebar() {
  return (
    <aside className="app-shell__sidebar">
      <Link className="sidebar__new-research" to={ROUTE_HOME}>
        + New research
      </Link>
      <SessionList />
    </aside>
  );
}
