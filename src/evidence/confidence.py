"""Claim confidence from measurable signals — never an LLM self-rating (§13).

confidence = source_quality × evidence_strength × source_agreement × extraction_confidence

- source_quality:       §6 normalized score of the best supporting source.
- evidence_strength:    claim↔passage embedding cosine similarity (reranker
                        skipped in v1; upgradeable to an NLI/entailment score).
- source_agreement:     min(distinct corroborating sources / 3, 1.0).
- extraction_confidence: calibrated extraction signal (self-consistency across
                        repeated extractions, or logprob), not a self-rating.
"""

from __future__ import annotations

from src.models.schemas import ConfidenceBreakdown


def compute_confidence(
    source_quality: float,
    evidence_strength: float,
    corroborating_sources: int,
    extraction_confidence: float,
) -> ConfidenceBreakdown:
    def clamp(x: float) -> float:
        return max(0.0, min(1.0, x))

    sq = clamp(source_quality)
    es = clamp(evidence_strength)
    agreement = min(corroborating_sources / 3.0, 1.0)
    ec = clamp(extraction_confidence)

    total = sq * es * agreement * ec
    return ConfidenceBreakdown(
        source_quality=round(sq, 4),
        evidence_strength=round(es, 4),
        source_agreement=round(agreement, 4),
        extraction_confidence=round(ec, 4),
        total=round(total, 4),
    )
