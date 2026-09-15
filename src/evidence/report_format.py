"""Pure report-formatting helpers for the synthesizer.

Rendering-only: turn claims, confidences, and contradictions into the report's
markdown fragments. No LLM or state mutation, so it lives apart from the
synthesizer's orchestration (CLAUDE.md rule 6).
"""

from __future__ import annotations

from src.evidence.citations import CitationIndex
from src.models.schemas import Claim, Contradiction, Evidence

CONFIDENCE_BAR_WIDTH = 20
PERCENT_MULTIPLIER = 100


def confidence_bar(value: float, width: int = CONFIDENCE_BAR_WIDTH) -> str:
    filled = round(value * width)
    percent = round(value * PERCENT_MULTIPLIER)
    return "█" * filled + "░" * (width - filled) + f" {percent}%"


def format_markers(markers: list[int]) -> str:
    return " ".join(f"[{number}]" for number in markers)


def render_conflicts(
    contradictions: list[Contradiction],
    claims: list[Claim],
    citations: CitationIndex,
    evidence: list[Evidence],
) -> list[str]:
    parts = ["## Conflicting Evidence", ""]
    if not contradictions:
        parts += ["No contradictions were detected among supported claims.", ""]
        return parts

    claim_by_id = {claim.id: claim for claim in claims}
    for contradiction in contradictions:
        claim_a = claim_by_id.get(contradiction.claim_a_id)
        claim_b = claim_by_id.get(contradiction.claim_b_id)
        if not claim_a or not claim_b:
            continue
        markers_a = citations.markers_for_claim(claim_a, evidence)
        markers_b = citations.markers_for_claim(claim_b, evidence)
        parts.append(
            f'- Conflict: "{claim_a.text}" {format_markers(markers_a)} '
            f'vs. "{claim_b.text}" {format_markers(markers_b)}'
        )
        parts.append(f"  - {contradiction.rationale}")
    parts.append("")
    return parts
