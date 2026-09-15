"""State ↔ ORM-row mapping round-trip.

Builds a fully populated ResearchState, converts it to (unpersisted) ORM rows,
then reconstructs a state from those rows and asserts the important fields
survive. This exercises the mapping logic without needing a live database.
"""

from __future__ import annotations

from src.db.mappers import (
    claim_rows_from_state,
    contradiction_rows_from_state,
    document_rows_from_state,
    entity_rows_from_state,
    evidence_rows_from_state,
    job_row_from_state,
    passage_rows_from_state,
    source_rows_from_state,
    state_from_rows,
    task_rows_from_state,
)
from src.models.schemas import (
    Claim,
    ClaimStatus,
    ConfidenceBreakdown,
    Contradiction,
    CostMeter,
    Document,
    Entity,
    Evidence,
    Passage,
    ResearchDepth,
    ResearchState,
    ResearchStatus,
    ResearchTask,
    Source,
    SourceQuality,
    SourceType,
)


def _populated_state() -> ResearchState:
    source = Source(
        url="https://docs.example.com/x",
        title="Docs",
        source_type=SourceType.DOCUMENTATION,
        quality=SourceQuality(authority=1.0, score=0.9),
    )
    document = Document(source_id=source.id, text="full text", content_hash="hash1")
    passage = Passage(
        document_id=document.id, source_id=source.id, text="Model X supports 128K.", ordinal=0
    )
    entity = Entity(name="Model X", type="model", aliases=["X"])
    claim = Claim(
        text="Model X supports 128K context.",
        subject_entity_id=entity.id,
        status=ClaimStatus.VERIFIED,
        confidence=0.7,
        confidence_breakdown=ConfidenceBreakdown(
            source_quality=0.9, evidence_strength=0.8, source_agreement=1.0,
            extraction_confidence=0.8, total=0.7,
        ),
    )
    evidence = Evidence(
        claim_id=claim.id, passage_id=passage.id, source_id=source.id,
        snippet="Model X supports 128K.", extraction_confidence=0.8, similarity=0.85,
    )
    claim.evidence_ids.append(evidence.id)
    contradiction = Contradiction(
        claim_a_id=claim.id, claim_b_id="claim_other", rationale="doc beats blog",
        resolved_winner_id=claim.id,
    )
    task = ResearchTask(
        sub_question="context length?", status=ResearchStatus.COMPLETED, source_ids=[source.id]
    )
    return ResearchState(
        original_question="What context length does Model X support?",
        depth=ResearchDepth.NORMAL,
        source_types=[SourceType.WEB, SourceType.DOCUMENTATION],
        status=ResearchStatus.COMPLETED,
        report="# Research Report\n...",
        research_tasks=[task],
        sources=[source],
        documents=[document],
        passages=[passage],
        entities=[entity],
        claims=[claim],
        evidence=[evidence],
        contradictions=[contradiction],
        cost=CostMeter(tokens_in=100, tokens_out=50, usd=0.001, latency_ms=1234),
    )


def test_state_survives_row_round_trip():
    original = _populated_state()

    restored = state_from_rows(
        job=job_row_from_state(original),
        tasks=task_rows_from_state(original),
        sources=source_rows_from_state(original),
        documents=document_rows_from_state(original),
        passages=passage_rows_from_state(original),
        entities=entity_rows_from_state(original),
        claims=claim_rows_from_state(original),
        evidence=evidence_rows_from_state(original),
        contradictions=contradiction_rows_from_state(original),
    )

    assert restored.research_id == original.research_id
    assert restored.original_question == original.original_question
    assert restored.depth == ResearchDepth.NORMAL
    assert restored.source_types == [SourceType.WEB, SourceType.DOCUMENTATION]
    assert restored.status == ResearchStatus.COMPLETED
    assert restored.report == original.report
    assert restored.cost.tokens_in == 100
    assert restored.cost.usd == 0.001

    assert restored.sources[0].quality.score == 0.9
    assert restored.sources[0].source_type == SourceType.DOCUMENTATION
    assert restored.documents[0].content_hash == "hash1"
    assert restored.passages[0].text == "Model X supports 128K."
    assert restored.entities[0].aliases == ["X"]

    restored_claim = restored.claims[0]
    assert restored_claim.status == ClaimStatus.VERIFIED
    assert restored_claim.confidence == 0.7
    assert restored_claim.confidence_breakdown.evidence_strength == 0.8
    assert restored_claim.evidence_ids == original.claims[0].evidence_ids

    assert restored.evidence[0].similarity == 0.85
    assert restored.contradictions[0].resolved_winner_id == restored_claim.id
    assert restored.research_tasks[0].source_ids == [original.sources[0].id]
