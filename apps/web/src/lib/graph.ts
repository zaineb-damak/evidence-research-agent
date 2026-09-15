// Helpers for querying the evidence graph on the client.

import type { EvidenceGraph } from "../api/types";

export const SUPPORTS_RELATION = "SUPPORTS";
export const CONTRADICTS_RELATION = "CONTRADICTS";
export const ABOUT_RELATION = "ABOUT";

export function sourceIdsSupportingClaim(
  graph: EvidenceGraph,
  claimId: string,
): string[] {
  return graph.edges
    .filter((edge) => edge.rel === SUPPORTS_RELATION && edge.src === claimId)
    .map((edge) => edge.dst);
}

export function claimIdsContradicting(
  graph: EvidenceGraph,
  claimId: string,
): string[] {
  return graph.edges
    .filter(
      (edge) =>
        edge.rel === CONTRADICTS_RELATION &&
        (edge.src === claimId || edge.dst === claimId),
    )
    .map((edge) => (edge.src === claimId ? edge.dst : edge.src));
}

export function relatedClaimIds(
  graph: EvidenceGraph,
  claimId: string,
): string[] {
  const subjectEntityIds = graph.edges
    .filter((edge) => edge.rel === ABOUT_RELATION && edge.src === claimId)
    .map((edge) => edge.dst);

  const siblings = new Set<string>();
  for (const entityId of subjectEntityIds) {
    for (const edge of graph.edges) {
      if (
        edge.rel === ABOUT_RELATION &&
        edge.dst === entityId &&
        edge.src !== claimId
      ) {
        siblings.add(edge.src);
      }
    }
  }
  return [...siblings];
}
