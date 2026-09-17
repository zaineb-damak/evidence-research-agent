// Adapted from the old top-level EvidenceExplorer.tsx: same data/logic
// (claim list + selected-claim detail panel), restyled onto ClaimList/
// ClaimDetail's flush-row treatment.

import { useMemo, useState } from "react";

import type { Claim, EvidenceGraph, Source } from "../../api/types";
import { ClaimDetail } from "./ClaimDetail";
import { ClaimList } from "./ClaimList";

interface EvidenceExplorerProps {
  claims: Claim[];
  sources: Source[];
  graph: EvidenceGraph;
}

const NO_SELECTION_MESSAGE = "Select a claim to explore its evidence.";

export function EvidenceExplorer({ claims, sources, graph }: EvidenceExplorerProps) {
  const [selectedClaimId, setSelectedClaimId] = useState<string | null>(claims[0]?.id ?? null);

  const claimsById = useMemo(() => new Map(claims.map((claim) => [claim.id, claim])), [claims]);
  const sourcesById = useMemo(
    () => new Map(sources.map((source) => [source.id, source])),
    [sources],
  );

  const selectedClaim =
    selectedClaimId === null ? null : (claimsById.get(selectedClaimId) ?? null);

  return (
    <div className="evidence-explorer">
      <aside className="evidence-explorer__claims">
        <h2 className="evidence-explorer__heading">Claims ({claims.length})</h2>
        <ClaimList
          claims={claims}
          selectedClaimId={selectedClaimId}
          onSelectClaim={setSelectedClaimId}
        />
      </aside>

      <main className="evidence-explorer__detail">
        {selectedClaim === null ? (
          <p className="evidence-explorer__empty">{NO_SELECTION_MESSAGE}</p>
        ) : (
          <ClaimDetail
            claim={selectedClaim}
            graph={graph}
            sourcesById={sourcesById}
            claimsById={claimsById}
            onSelectClaim={setSelectedClaimId}
          />
        )}
      </main>
    </div>
  );
}
