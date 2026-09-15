import {
  CLAIM_STATUS_COLORS,
  CLAIM_STATUS_LABELS,
} from "../constants";
import { confidenceBar, toPercent } from "../lib/format";
import {
  claimIdsContradicting,
  relatedClaimIds,
  sourceIdsSupportingClaim,
} from "../lib/graph";
import type { Claim, EvidenceGraph, Source } from "../api/types";

interface ClaimDetailProps {
  claim: Claim;
  graph: EvidenceGraph;
  sourcesById: Map<string, Source>;
  claimsById: Map<string, Claim>;
  onSelectClaim: (claimId: string) => void;
}

export function ClaimDetail({
  claim,
  graph,
  sourcesById,
  claimsById,
  onSelectClaim,
}: ClaimDetailProps) {
  const supportingSourceIds = sourceIdsSupportingClaim(graph, claim.id);
  const contradictingClaimIds = claimIdsContradicting(graph, claim.id);
  const relatedIds = relatedClaimIds(graph, claim.id);

  return (
    <div className="claim-detail">
      <h3>{claim.text}</h3>
      <p
        className="status"
        style={{ color: CLAIM_STATUS_COLORS[claim.status] }}
      >
        {CLAIM_STATUS_LABELS[claim.status]}
      </p>

      <p className="confidence">
        <code>{confidenceBar(claim.confidence)}</code>{" "}
        {toPercent(claim.confidence)}%
      </p>

      <ConfidenceFactors claim={claim} />

      <section>
        <h4>Supporting evidence</h4>
        <SourceList sourceIds={supportingSourceIds} sourcesById={sourcesById} />
      </section>

      <section>
        <h4>Contradicting evidence</h4>
        {contradictingClaimIds.length === 0 ? (
          <p className="muted">None detected.</p>
        ) : (
          <ClaimLinks
            claimIds={contradictingClaimIds}
            claimsById={claimsById}
            onSelectClaim={onSelectClaim}
          />
        )}
      </section>

      <section>
        <h4>Related claims</h4>
        {relatedIds.length === 0 ? (
          <p className="muted">None.</p>
        ) : (
          <ClaimLinks
            claimIds={relatedIds}
            claimsById={claimsById}
            onSelectClaim={onSelectClaim}
          />
        )}
      </section>
    </div>
  );
}

function ConfidenceFactors({ claim }: { claim: Claim }) {
  const breakdown = claim.confidence_breakdown;
  const factors: { label: string; value: number }[] = [
    { label: "Source quality", value: breakdown.source_quality },
    { label: "Evidence strength", value: breakdown.evidence_strength },
    { label: "Source agreement", value: breakdown.source_agreement },
    { label: "Extraction confidence", value: breakdown.extraction_confidence },
  ];
  return (
    <ul className="factors">
      {factors.map((factor) => (
        <li key={factor.label}>
          {factor.label}: {toPercent(factor.value)}%
        </li>
      ))}
    </ul>
  );
}

function SourceList({
  sourceIds,
  sourcesById,
}: {
  sourceIds: string[];
  sourcesById: Map<string, Source>;
}) {
  if (sourceIds.length === 0) {
    return <p className="muted">No sources linked.</p>;
  }
  return (
    <ul className="source-list">
      {sourceIds.map((sourceId) => {
        const source = sourcesById.get(sourceId);
        if (!source) {
          return null;
        }
        return (
          <li key={sourceId}>
            <a href={source.url} target="_blank" rel="noreferrer">
              {source.title ?? source.url}
            </a>
            <span className="source-meta">
              {" "}
              · {source.source_type} · quality{" "}
              {toPercent(source.quality.score)}%
            </span>
          </li>
        );
      })}
    </ul>
  );
}

function ClaimLinks({
  claimIds,
  claimsById,
  onSelectClaim,
}: {
  claimIds: string[];
  claimsById: Map<string, Claim>;
  onSelectClaim: (claimId: string) => void;
}) {
  return (
    <ul className="claim-links">
      {claimIds.map((claimId) => {
        const linkedClaim = claimsById.get(claimId);
        if (!linkedClaim) {
          return null;
        }
        return (
          <li key={claimId}>
            <button type="button" onClick={() => onSelectClaim(claimId)}>
              {linkedClaim.text}
            </button>
          </li>
        );
      })}
    </ul>
  );
}
