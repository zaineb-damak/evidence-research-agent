import { Link } from "react-router-dom";

import type { ResearchJobListItem } from "../../api/types";
import { RESEARCH_STATUS_TONE } from "../../constants";
import { formatRelativeTime } from "../../lib/format";
import { buildResearchPath } from "../../routes";

interface SessionListItemProps {
  session: ResearchJobListItem;
}

export function SessionListItem({ session }: SessionListItemProps) {
  // RESEARCH_STATUS_TONE values ("verified" | "pending" | "contradiction")
  // are exactly the tokens.css custom property names for the three signal
  // colors, so the dot's color is derived directly with no extra lookup.
  const tone = RESEARCH_STATUS_TONE[session.status];

  return (
    <li className="session-list__item">
      <Link
        className="session-list__link"
        to={buildResearchPath(session.research_id)}
        title={session.question}
      >
        <span
          className="session-list__status-dot"
          style={{ backgroundColor: `var(--${tone})` }}
          aria-hidden="true"
        />
        <span className="session-list__question">{session.question}</span>
        <span className="session-list__time">
          {formatRelativeTime(new Date(session.updated_at))}
        </span>
      </Link>
    </li>
  );
}
