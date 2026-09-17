// React Query wrapper for the finished-job reads (claims/sources/graph/report).
// Unlike the live SSE stream, these are plain immutable-once-completed
// request/response resources, so caching by research id makes revisiting a
// past session from history instant instead of re-fetching every tab.

import { useQuery } from "@tanstack/react-query";
import type { UseQueryResult } from "@tanstack/react-query";

import { getClaims, getGraph, getReport, getSources } from "../api/client";
import type { Claim, EvidenceGraph, ReportResponse, Source } from "../api/types";

export interface ResearchResults {
  claims: UseQueryResult<Claim[]>;
  sources: UseQueryResult<Source[]>;
  graph: UseQueryResult<EvidenceGraph>;
  report: UseQueryResult<ReportResponse>;
  isLoading: boolean;
  isError: boolean;
}

export function researchResultsQueryKey(
  resource: "claims" | "sources" | "graph" | "report",
  researchId: string,
): readonly [string, string] {
  return [resource, researchId] as const;
}

// enabled: false lets a caller build the hook unconditionally (hooks can't be
// called conditionally) while still holding off the network calls until the
// job is actually known to be finished (see pages/ResearchPage.tsx).
export function useResearchResults(researchId: string, enabled: boolean): ResearchResults {
  const claims = useQuery({
    queryKey: researchResultsQueryKey("claims", researchId),
    queryFn: () => getClaims(researchId),
    enabled,
  });
  const sources = useQuery({
    queryKey: researchResultsQueryKey("sources", researchId),
    queryFn: () => getSources(researchId),
    enabled,
  });
  const graph = useQuery({
    queryKey: researchResultsQueryKey("graph", researchId),
    queryFn: () => getGraph(researchId),
    enabled,
  });
  const report = useQuery({
    queryKey: researchResultsQueryKey("report", researchId),
    queryFn: () => getReport(researchId),
    enabled,
  });

  return {
    claims,
    sources,
    graph,
    report,
    isLoading: claims.isLoading || sources.isLoading || graph.isLoading || report.isLoading,
    isError: claims.isError || sources.isError || graph.isError || report.isError,
  };
}
