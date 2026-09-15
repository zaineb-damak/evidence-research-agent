"""Citation metrics (§21).

- correctness  = supported cited claims / cited claims       (target > 0.95)
- completeness = claims with citations / claims requiring one (target > 0.95)

A claim is "supported" when at least one of its citations resolves to real
evidence. Important claims (anything not explicitly unsupported) require a
citation.
"""

from __future__ import annotations

from src.models.schemas import Claim, ClaimStatus, Evidence

PERFECT_SCORE = 1.0

CITATION_CORRECTNESS_TARGET = 0.95
CITATION_COMPLETENESS_TARGET = 0.95


def _has_resolvable_evidence(claim: Claim, evidence_ids: set[str]) -> bool:
    return any(evidence_id in evidence_ids for evidence_id in claim.evidence_ids)


def citation_correctness(claims: list[Claim], evidence: list[Evidence]) -> float:
    evidence_ids = {item.id for item in evidence}
    cited_claims = [claim for claim in claims if claim.evidence_ids]
    if not cited_claims:
        return PERFECT_SCORE
    supported = sum(
        1 for claim in cited_claims if _has_resolvable_evidence(claim, evidence_ids)
    )
    return supported / len(cited_claims)


def citation_completeness(claims: list[Claim]) -> float:
    claims_requiring_citation = [
        claim for claim in claims if claim.status != ClaimStatus.UNSUPPORTED
    ]
    if not claims_requiring_citation:
        return PERFECT_SCORE
    with_citation = sum(1 for claim in claims_requiring_citation if claim.evidence_ids)
    return with_citation / len(claims_requiring_citation)
