"""Convert between domain schemas (Pydantic) and ORM rows (SQLAlchemy).

Kept separate from the repository so the persistence logic reads as pure
save/load orchestration and the field-by-field mapping lives in one place.
"""

from __future__ import annotations

from src.models.db import (
    ClaimRow,
    ContradictionRow,
    DocumentRow,
    EntityRow,
    EvidenceRow,
    PassageRow,
    ResearchJobRow,
    ResearchTaskRow,
    SourceRow,
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


def job_row_from_state(state: ResearchState) -> ResearchJobRow:
    return ResearchJobRow(
        id=state.research_id,
        owner_user_id=state.owner_user_id,
        owner_session_id=state.owner_session_id,
        question=state.original_question,
        depth=state.depth.value,
        source_types=[source_type.value for source_type in state.source_types],
        status=state.status.value,
        error=state.error,
        report=state.report,
        tokens_in=state.cost.tokens_in,
        tokens_out=state.cost.tokens_out,
        cost_usd=state.cost.usd,
        latency_ms=state.cost.latency_ms,
    )


def task_rows_from_state(state: ResearchState) -> list[ResearchTaskRow]:
    return [
        ResearchTaskRow(
            id=task.id,
            job_id=state.research_id,
            sub_question=task.sub_question,
            status=task.status.value,
            source_ids=list(task.source_ids),
        )
        for task in state.research_tasks
    ]


def source_rows_from_state(state: ResearchState) -> list[SourceRow]:
    return [
        SourceRow(
            id=source.id,
            job_id=state.research_id,
            url=source.url,
            title=source.title,
            domain=source.domain,
            source_type=source.source_type.value,
            published_at=source.published_at,
            retrieved_at=source.retrieved_at,
            author=source.author,
            language=source.language,
            quality=source.quality.model_dump(),
        )
        for source in state.sources
    ]


def passage_rows_from_state(state: ResearchState) -> list[PassageRow]:
    return [
        PassageRow(
            id=passage.id,
            job_id=state.research_id,
            document_id=passage.document_id,
            source_id=passage.source_id,
            text=passage.text,
            ordinal=passage.ordinal,
            qdrant_point_id=passage.qdrant_point_id,
        )
        for passage in state.passages
    ]


def entity_rows_from_state(state: ResearchState) -> list[EntityRow]:
    return [
        EntityRow(
            id=entity.id,
            job_id=state.research_id,
            name=entity.name,
            type=entity.type,
            aliases=list(entity.aliases),
        )
        for entity in state.entities
    ]


def claim_rows_from_state(state: ResearchState) -> list[ClaimRow]:
    return [
        ClaimRow(
            id=claim.id,
            job_id=state.research_id,
            text=claim.text,
            subject_entity_id=claim.subject_entity_id,
            status=claim.status.value,
            confidence=claim.confidence,
            confidence_breakdown=claim.confidence_breakdown.model_dump(),
            evidence_ids=list(claim.evidence_ids),
        )
        for claim in state.claims
    ]


def evidence_rows_from_state(state: ResearchState) -> list[EvidenceRow]:
    return [
        EvidenceRow(
            id=item.id,
            job_id=state.research_id,
            claim_id=item.claim_id,
            passage_id=item.passage_id,
            source_id=item.source_id,
            snippet=item.snippet,
            extraction_confidence=item.extraction_confidence,
            similarity=item.similarity,
        )
        for item in state.evidence
    ]


def contradiction_rows_from_state(state: ResearchState) -> list[ContradictionRow]:
    return [
        ContradictionRow(
            id=contradiction.id,
            job_id=state.research_id,
            claim_a_id=contradiction.claim_a_id,
            claim_b_id=contradiction.claim_b_id,
            rationale=contradiction.rationale,
            resolved_winner_id=contradiction.resolved_winner_id,
        )
        for contradiction in state.contradictions
    ]


def document_rows_from_state(state: ResearchState) -> list[DocumentRow]:
    return [
        DocumentRow(
            id=document.id,
            job_id=state.research_id,
            source_id=document.source_id,
            text=document.text,
            content_hash=document.content_hash,
        )
        for document in state.documents
    ]


def state_from_rows(
    job: ResearchJobRow,
    tasks: list[ResearchTaskRow],
    sources: list[SourceRow],
    documents: list[DocumentRow],
    passages: list[PassageRow],
    entities: list[EntityRow],
    claims: list[ClaimRow],
    evidence: list[EvidenceRow],
    contradictions: list[ContradictionRow],
) -> ResearchState:
    return ResearchState(
        research_id=job.id,
        owner_user_id=job.owner_user_id,
        owner_session_id=job.owner_session_id,
        original_question=job.question,
        depth=ResearchDepth(job.depth),
        source_types=[SourceType(value) for value in job.source_types],
        status=ResearchStatus(job.status),
        error=job.error,
        report=job.report,
        cost=CostMeter(
            tokens_in=job.tokens_in,
            tokens_out=job.tokens_out,
            usd=job.cost_usd,
            latency_ms=job.latency_ms,
        ),
        research_tasks=[
            ResearchTask(
                id=task.id,
                sub_question=task.sub_question,
                status=ResearchStatus(task.status),
                source_ids=list(task.source_ids),
            )
            for task in tasks
        ],
        sources=[
            Source(
                id=source.id,
                url=source.url,
                title=source.title,
                domain=source.domain,
                source_type=SourceType(source.source_type),
                published_at=source.published_at,
                retrieved_at=source.retrieved_at,
                author=source.author,
                language=source.language,
                quality=SourceQuality(**source.quality),
            )
            for source in sources
        ],
        documents=[
            Document(
                id=document.id,
                source_id=document.source_id,
                text=document.text,
                content_hash=document.content_hash,
            )
            for document in documents
        ],
        passages=[
            Passage(
                id=passage.id,
                document_id=passage.document_id,
                source_id=passage.source_id,
                text=passage.text,
                ordinal=passage.ordinal,
                qdrant_point_id=passage.qdrant_point_id,
            )
            for passage in passages
        ],
        entities=[
            Entity(id=entity.id, name=entity.name, type=entity.type, aliases=list(entity.aliases))
            for entity in entities
        ],
        claims=[
            Claim(
                id=claim.id,
                text=claim.text,
                subject_entity_id=claim.subject_entity_id,
                status=ClaimStatus(claim.status),
                confidence=claim.confidence,
                confidence_breakdown=ConfidenceBreakdown(**claim.confidence_breakdown),
                evidence_ids=list(claim.evidence_ids),
            )
            for claim in claims
        ],
        evidence=[
            Evidence(
                id=item.id,
                claim_id=item.claim_id,
                passage_id=item.passage_id,
                source_id=item.source_id,
                snippet=item.snippet,
                extraction_confidence=item.extraction_confidence,
                similarity=item.similarity,
            )
            for item in evidence
        ],
        contradictions=[
            Contradiction(
                id=contradiction.id,
                claim_a_id=contradiction.claim_a_id,
                claim_b_id=contradiction.claim_b_id,
                rationale=contradiction.rationale,
                resolved_winner_id=contradiction.resolved_winner_id,
            )
            for contradiction in contradictions
        ],
    )
