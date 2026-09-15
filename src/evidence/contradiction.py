"""Contradiction adjudication (§9).

Takes the contradiction candidates surfaced by resolution (same subject +
attribute, conflicting values) and turns each into a Contradiction with a
rationale and a resolved winner. The winner is chosen by measurable source
signals — primary-source status and recency — never silently.
"""

from __future__ import annotations

from src.evidence.source_selection import best_source_for_claim, describe_source
from src.models.schemas import Claim, Contradiction, Evidence, Source


def detect_contradictions(
    candidates: list[tuple[str, str]],
    claims: list[Claim],
    evidence: list[Evidence],
    sources: list[Source],
) -> list[Contradiction]:
    claim_by_id = {claim.id: claim for claim in claims}
    sources_by_id = {source.id: source for source in sources}
    contradictions: list[Contradiction] = []

    for claim_a_id, claim_b_id in candidates:
        claim_a = claim_by_id.get(claim_a_id)
        claim_b = claim_by_id.get(claim_b_id)
        if not claim_a or not claim_b:
            continue
        source_a = best_source_for_claim(claim_a, evidence, sources_by_id)
        source_b = best_source_for_claim(claim_b, evidence, sources_by_id)

        # Winner: higher source quality (which already blends authority + recency).
        winner_id = None
        if source_a and source_b:
            winner_id = (
                claim_a_id
                if source_a.quality.score >= source_b.quality.score
                else claim_b_id
            )
        elif source_a:
            winner_id = claim_a_id
        elif source_b:
            winner_id = claim_b_id

        winner_label = "A" if winner_id == claim_a_id else "B"
        rationale = (
            f'"{claim_a.text}" is reported by {describe_source(source_a)}, while '
            f'"{claim_b.text}" is reported by {describe_source(source_b)}. Treating '
            f"claim {winner_label} as authoritative based on source quality; both "
            "are surfaced in the report."
        )
        contradictions.append(
            Contradiction(
                claim_a_id=claim_a_id,
                claim_b_id=claim_b_id,
                rationale=rationale,
                resolved_winner_id=winner_id,
            )
        )
    return contradictions
