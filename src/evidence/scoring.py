"""Compute measurable claim confidence and fold entities into research state.

Extracted from the workflow so orchestration stays thin. Confidence uses only
measurable signals (source quality, cosine evidence strength, corroboration,
extraction confidence) — never an LLM self-rating. Claim status is deliberately
left for the Verifier; this module only fills in the numbers.
"""

from __future__ import annotations

from langchain_core.embeddings import Embeddings

from src.evidence.confidence import compute_confidence
from src.models.schemas import Claim, ClaimStatus, Entity, Evidence, Source
from src.retrieval.semantic import cosine
from src.sources.quality import score_source

SIMILARITY_ROUNDING_DECIMALS = 4
MINIMUM_SIMILARITY = 0.0

# Placeholder until self-consistency across repeated extractions is wired.
# A neutral constant, explicitly not an LLM self-rating.
DEFAULT_EXTRACTION_CONFIDENCE = 0.8


def merge_entities(existing_entities: list[Entity], new_entities: list[Entity]) -> None:
    """Append entities whose names are not already present (case-insensitive)."""
    known_names = {entity.name.lower() for entity in existing_entities}
    for entity in new_entities:
        normalized_name = entity.name.lower()
        if normalized_name not in known_names:
            existing_entities.append(entity)
            known_names.add(normalized_name)


def score_claim_confidence(
    claims: list[Claim],
    evidence: list[Evidence],
    sources: list[Source],
    passage_vectors: dict[str, list[float]],
    embeddings: Embeddings,
) -> None:
    """Fill confidence + breakdown on each claim in place using measurable signals."""
    source_by_id = {source.id: source for source in sources}
    evidence_by_id = {item.id: item for item in evidence}

    for claim in claims:
        supporting_evidence = [
            evidence_by_id[evidence_id]
            for evidence_id in claim.evidence_ids
            if evidence_id in evidence_by_id
        ]
        if not supporting_evidence:
            claim.status = ClaimStatus.UNSUPPORTED
            continue

        claim_vector = embeddings.embed_query(claim.text)
        best_evidence_strength = MINIMUM_SIMILARITY
        best_source_quality = MINIMUM_SIMILARITY
        distinct_source_ids = {item.source_id for item in supporting_evidence}

        for evidence_item in supporting_evidence:
            passage_vector = passage_vectors.get(evidence_item.passage_id)
            if passage_vector:
                strength = max(MINIMUM_SIMILARITY, cosine(claim_vector, passage_vector))
                evidence_item.similarity = round(strength, SIMILARITY_ROUNDING_DECIMALS)
                best_evidence_strength = max(best_evidence_strength, strength)

            source = source_by_id.get(evidence_item.source_id)
            if source:
                quality = score_source(
                    source,
                    relevance=evidence_item.similarity,
                    corroboration_count=len(distinct_source_ids),
                )
                source.quality = quality
                best_source_quality = max(best_source_quality, quality.score)

            evidence_item.extraction_confidence = DEFAULT_EXTRACTION_CONFIDENCE

        breakdown = compute_confidence(
            source_quality=best_source_quality,
            evidence_strength=best_evidence_strength,
            corroborating_sources=len(distinct_source_ids),
            extraction_confidence=DEFAULT_EXTRACTION_CONFIDENCE,
        )
        claim.confidence_breakdown = breakdown
        claim.confidence = breakdown.total
        # Status stays UNVERIFIED here; the Verifier assigns the final status
        # (VERIFIED / PARTIALLY_SUPPORTED / CONFLICTING / UNSUPPORTED).
