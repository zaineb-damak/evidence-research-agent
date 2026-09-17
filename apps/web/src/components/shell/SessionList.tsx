// Session-history list backing the sidebar. Groups the user's research jobs
// into sentence-case "Today"/"Earlier" sections by comparing created_at to
// the start of the current local day.

import { useSessions } from "../../hooks/useSessions";
import type { ResearchJobListItem } from "../../api/types";
import { isToday } from "../../lib/format";
import { SessionListItem } from "./SessionListItem";

const SECTION_LABEL_TODAY = "Today";
const SECTION_LABEL_EARLIER = "Earlier";

const EMPTY_STATE_MESSAGE =
  "Nothing here yet. Ask your first research question to start one.";
const LOADING_MESSAGE = "Loading…";
const ERROR_MESSAGE = "Couldn't load your research history.";

function groupByDay(
  sessions: ResearchJobListItem[],
): { label: string; items: ResearchJobListItem[] }[] {
  const today: ResearchJobListItem[] = [];
  const earlier: ResearchJobListItem[] = [];

  for (const session of sessions) {
    if (isToday(new Date(session.created_at))) {
      today.push(session);
    } else {
      earlier.push(session);
    }
  }

  const groups: { label: string; items: ResearchJobListItem[] }[] = [];
  if (today.length > 0) {
    groups.push({ label: SECTION_LABEL_TODAY, items: today });
  }
  if (earlier.length > 0) {
    groups.push({ label: SECTION_LABEL_EARLIER, items: earlier });
  }
  return groups;
}

export function SessionList() {
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

  return (
    <nav className="session-list" aria-label="Research history">
      {groupByDay(sessions).map((group) => (
        <div className="session-list__group" key={group.label}>
          <h2 className="session-list__heading">{group.label}</h2>
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
