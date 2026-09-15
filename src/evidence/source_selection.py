"""Pick and describe the best source backing a claim.

Used by contradiction adjudication to choose a winner by measurable source
signals. Kept apart from the adjudication logic (CLAUDE.md rule 6).
"""

from __future__ import annotations

from src.models.schemas import Claim, Evidence, Source

UNATTRIBUTED_SOURCE = "an unattributed source"
UNDATED = "undated"


def best_source_for_claim(
    claim: Claim, evidence: list[Evidence], sources_by_id: dict[str, Source]
) -> Source | None:
    evidence_ids = set(claim.evidence_ids)
    claim_evidence = [item for item in evidence if item.id in evidence_ids]
    source_ids = {item.source_id for item in claim_evidence}
    candidate_sources = [sources_by_id[sid] for sid in source_ids if sid in sources_by_id]
    if not candidate_sources:
        return None
    return max(candidate_sources, key=lambda source: source.quality.score)


def describe_source(source: Source | None) -> str:
    if not source:
        return UNATTRIBUTED_SOURCE
    published = source.published_at.date().isoformat() if source.published_at else UNDATED
    return f"{source.source_type} source ({published})"
