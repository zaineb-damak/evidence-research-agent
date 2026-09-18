// Run history for the sidebar: the caller's research jobs (GET /api/research),
// filtered by the sidebar's search field and grouped by recency.

import { useSessions } from "../../hooks/useSessions";
import { filterSessions, groupSessionsByRecency } from "../../lib/sessionGroups";
import { SessionListItem } from "./SessionListItem";

const EMPTY_STATE_MESSAGE = "Nothing here yet. Ask your first research question to start one.";
const NO_MATCHES_MESSAGE = "No runs match that search.";
const LOADING_MESSAGE = "Loading…";
const ERROR_MESSAGE = "Couldn't load your research history.";
const HISTORY_LABEL = "Research history";

interface SessionListProps {
  searchQuery: string;
}

export function SessionList({ searchQuery }: SessionListProps) {
  const { data, isLoading, isError } = useSessions();

  if (isLoading) {
    return <p className="session-list__status">{LOADING_MESSAGE}</p>;
  }

  if (isError) {
    return <p className="session-list__status">{ERROR_MESSAGE}</p>;
  }

  const sessions = data ?? [];

  if (sessions.length === 0) {
    return <p className="session-list__empty">{EMPTY_STATE_MESSAGE}</p>;
  }

  const matches = filterSessions(sessions, searchQuery);

  if (matches.length === 0) {
    return <p className="session-list__empty">{NO_MATCHES_MESSAGE}</p>;
  }

  return (
    <nav className="session-list" aria-label={HISTORY_LABEL}>
      {groupSessionsByRecency(matches).map((group) => (
        <div className="session-list__group" key={group.label}>
          <h2 className="eyebrow session-list__heading">{group.label}</h2>
          <ul className="session-list__items">
            {group.items.map((session) => (
              <SessionListItem key={session.research_id} session={session} />
            ))}
          </ul>
        </div>
      ))}
    </nav>
  );
}
