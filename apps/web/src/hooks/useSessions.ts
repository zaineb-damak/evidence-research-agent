import { useQuery } from "@tanstack/react-query";
import type { UseQueryResult } from "@tanstack/react-query";

import { getSessions } from "../api/client";
import type { ResearchJobListItem } from "../api/types";

// Query key for the session-history list (GET /api/research). When the
// research-creation flow (HomePage, separate/later work) enqueues a new job,
// it should call `queryClient.invalidateQueries({ queryKey: SESSIONS_QUERY_KEY })`
// so the sidebar picks up the new session without a manual refresh.
export const SESSIONS_QUERY_KEY = ["sessions"] as const;

export function useSessions(): UseQueryResult<ResearchJobListItem[]> {
  return useQuery({
    queryKey: SESSIONS_QUERY_KEY,
    queryFn: getSessions,
  });
}
