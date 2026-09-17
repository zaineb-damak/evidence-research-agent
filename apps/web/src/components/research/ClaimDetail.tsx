// Adapted from the old top-level ClaimDetail.tsx: same data/logic (confidence
// breakdown, supporting sources, contradicting/related claims resolved from
// the evidence graph), restyled — a colored status rail instead of a bordered
// box, SourceMeta instead of a dot-joined meta string, a plain percentage bar
// instead of an ASCII/monospace confidence meter (mono is reserved for
// literal machine data, not stat labels).

import { CLAIM_STATUS_LABELS, CLAIM_STATUS_TONE } from "../../constants";
import { toPercent } from "../../lib/format";
import {
  claimIdsContradicting,
  relatedClaimIds,
  sourceIdsSupportingClaim,
} from "../../lib/graph";
import type { Claim, EvidenceGraph, Source } from "../../api/types";
import { SourceMeta } from "./SourceMeta";

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
  const tone = CLAIM_STATUS_TONE[claim.status];

  return (
    <div className={`claim-detail claim-detail--${tone}`}>
      <h2 className="claim-detail__text">{claim.text}</h2>
      <p className="claim-detail__status">{CLAIM_STATUS_LABELS[claim.status]}</p>

      <ConfidenceMeter confidence={claim.confidence} />
      <ConfidenceFactors claim={claim} />

      <section className="claim-detail__section">
        <h3 className="claim-detail__section-title">Supporting evidence</h3>
        <SourceList sourceIds={supportingSourceIds} sourcesById={sourcesById} />
      </section>

      <section className="claim-detail__section">
        <h3 className="claim-detail__section-title">Contradicting evidence</h3>
        {contradictingClaimIds.length === 0 ? (
          <p className="claim-detail__muted">None detected.</p>
        ) : (
          <ClaimLinks
            claimIds={contradictingClaimIds}
            claimsById={claimsById}
            onSelectClaim={onSelectClaim}
          />
        )}
      </section>

      <section className="claim-detail__section">
        <h3 className="claim-detail__section-title">Related claims</h3>
        {relatedIds.length === 0 ? (
          <p className="claim-detail__muted">None.</p>
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

function ConfidenceMeter({ confidence }: { confidence: number }) {
  const percent = toPercent(confidence);
  return (
    <div className="claim-detail__confidence" role="img" aria-label={`Confidence ${percent}%`}>
      <div className="claim-detail__confidence-track">
        <div className="claim-detail__confidence-fill" style={{ width: `${percent}%` }} />
      </div>
      <span className="claim-detail__confidence-value">{percent}%</span>
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
    <ul className="claim-detail__factors">
      {factors.map((factor) => (
        <li key={factor.label} className="claim-detail__factor">
          <span className="claim-detail__factor-label">{factor.label}</span>
          <span className="claim-detail__factor-value">{toPercent(factor.value)}%</span>
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
    return <p className="claim-detail__muted">No sources linked.</p>;
  }
  return (
    <ul className="claim-detail__source-list">
      {sourceIds.map((sourceId) => {
        const source = sourcesById.get(sourceId);
        if (!source) {
          return null;
        }
        return (
          <li key={sourceId} className="claim-detail__source">
            <a href={source.url} target="_blank" rel="noreferrer">
              {source.title ?? source.url}
            </a>
            <SourceMeta sourceType={source.source_type} qualityScore={source.quality.score} />
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
    <ul className="claim-detail__claim-links">
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
