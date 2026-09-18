// Pure helpers for the sidebar's run history: text filtering and grouping by
// recency ("Today" / "Previous 7 days" / "Older"), kept out of the component
// so both are testable on their own (CLAUDE.md rule 6).

import type { ResearchJobListItem } from "../api/types";
import { startOfLocalDay } from "./format";

export const SESSION_GROUP_LABEL_TODAY = "Today";
export const SESSION_GROUP_LABEL_RECENT = "Previous 7 days";
export const SESSION_GROUP_LABEL_OLDER = "Older";

// "Previous 7 days" covers the seven local days before today.
const RECENT_WINDOW_DAYS = 7;

export interface SessionGroup {
  label: string;
  items: ResearchJobListItem[];
}

export function filterSessions(
  sessions: ResearchJobListItem[],
  searchQuery: string,
): ResearchJobListItem[] {
  const normalizedQuery = searchQuery.trim().toLowerCase();
  if (normalizedQuery === "") {
    return sessions;
  }
  return sessions.filter((session) =>
    session.question.toLowerCase().includes(normalizedQuery),
  );
}

export function groupSessionsByRecency(
  sessions: ResearchJobListItem[],
  now: Date = new Date(),
): SessionGroup[] {
  const today = startOfLocalDay(now);
  const recentWindowStart = new Date(today);
  recentWindowStart.setDate(recentWindowStart.getDate() - RECENT_WINDOW_DAYS);

  const buckets: Record<string, ResearchJobListItem[]> = {
    [SESSION_GROUP_LABEL_TODAY]: [],
    [SESSION_GROUP_LABEL_RECENT]: [],
    [SESSION_GROUP_LABEL_OLDER]: [],
  };

  for (const session of sessions) {
    const createdDay = startOfLocalDay(new Date(session.created_at));
    if (createdDay.getTime() >= today.getTime()) {
      buckets[SESSION_GROUP_LABEL_TODAY].push(session);
    } else if (createdDay.getTime() > recentWindowStart.getTime()) {
      buckets[SESSION_GROUP_LABEL_RECENT].push(session);
    } else {
      buckets[SESSION_GROUP_LABEL_OLDER].push(session);
    }
  }

  return Object.entries(buckets)
    .filter(([, items]) => items.length > 0)
    .map(([label, items]) => ({ label, items }));
}
