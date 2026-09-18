// One history row. NavLink drives the selected treatment (the design's white
// row with an accent dot) through aria-current="page", so no separate
// "is this the open run" prop is threaded down.

import { NavLink } from "react-router-dom";

import type { ResearchJobListItem } from "../../api/types";
import { buildResearchPath } from "../../routes";

interface SessionListItemProps {
  session: ResearchJobListItem;
}

export function SessionListItem({ session }: SessionListItemProps) {
  return (
    <li className="session-list__item">
      <NavLink
        className="session-list__link"
        to={buildResearchPath(session.research_id)}
        title={session.question}
      >
        <span className="session-list__status-dot" aria-hidden="true" />
        <span className="session-list__question">{session.question}</span>
      </NavLink>
    </li>
  );
}
