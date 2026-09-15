import { useMemo, useState } from "react";

import { CLAIM_STATUS_COLORS, CLAIM_STATUS_LABELS } from "../constants";
import { toPercent } from "../lib/format";
import { ClaimDetail } from "./ClaimDetail";
import type { Claim, EvidenceGraph, Source } from "../api/types";

interface EvidenceExplorerProps {
  claims: Claim[];
  sources: Source[];
  graph: EvidenceGraph;
}

export function EvidenceExplorer({
  claims,
  sources,
  graph,
}: EvidenceExplorerProps) {
  const [selectedClaimId, setSelectedClaimId] = useState<string | null>(
    claims[0]?.id ?? null,
  );

  const claimsById = useMemo(
    () => new Map(claims.map((claim) => [claim.id, claim])),
    [claims],
  );
  const sourcesById = useMemo(
    () => new Map(sources.map((source) => [source.id, source])),
    [sources],
  );

  const selectedClaim =
    selectedClaimId === null ? null : (claimsById.get(selectedClaimId) ?? null);

  return (
    <div className="evidence-explorer">
      <aside className="claim-list">
        <h2>Claims ({claims.length})</h2>
        <ul>
          {claims.map((claim) => (
            <li key={claim.id}>
              <button
                type="button"
                className={claim.id === selectedClaimId ? "selected" : ""}
                onClick={() => setSelectedClaimId(claim.id)}
              >
                <span
                  className="dot"
                  style={{ background: CLAIM_STATUS_COLORS[claim.status] }}
                  title={CLAIM_STATUS_LABELS[claim.status]}
                />
                {claim.text}
                <span className="confidence-pill">
                  {toPercent(claim.confidence)}%
                </span>
              </button>
            </li>
          ))}
        </ul>
      </aside>

      <main className="claim-panel">
        {selectedClaim === null ? (
          <p className="muted">Select a claim to explore its evidence.</p>
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
