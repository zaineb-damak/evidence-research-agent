"""Job repository: the durable store of research jobs and their evidence.

`PostgresJobRepository` is the production system of record. `InMemoryJobRepository`
is a test double with identical behavior, so the API and worker can be exercised
without a live database. Both satisfy the `JobRepository` protocol.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from sqlalchemy import delete, select

from src.clock import utcnow
from src.db.base import session_scope
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
from src.models.schemas import ResearchRequest, ResearchState, ResearchStatus

# Child tables cleared and rewritten on each save (keyed by job_id).
_CHILD_ROW_TYPES = (
    ResearchTaskRow,
    SourceRow,
    DocumentRow,
    PassageRow,
    EntityRow,
    ClaimRow,
    EvidenceRow,
    ContradictionRow,
)


@runtime_checkable
class JobRepository(Protocol):
    def create(
        self,
        request: ResearchRequest,
        owner_user_id: str | None = None,
        owner_session_id: str | None = None,
    ) -> ResearchState: ...

    def get(self, research_id: str) -> ResearchState | None: ...

    def save(self, state: ResearchState) -> None: ...


def _new_state(
    request: ResearchRequest,
    owner_user_id: str | None,
    owner_session_id: str | None,
) -> ResearchState:
    return ResearchState(
        original_question=request.question,
        depth=request.depth,
        source_types=request.source_types,
        status=ResearchStatus.QUEUED,
        owner_user_id=owner_user_id,
        owner_session_id=owner_session_id,
    )


class PostgresJobRepository:
    def create(
        self,
        request: ResearchRequest,
        owner_user_id: str | None = None,
        owner_session_id: str | None = None,
    ) -> ResearchState:
        state = _new_state(request, owner_user_id, owner_session_id)
        self.save(state)
        return state

    def get(self, research_id: str) -> ResearchState | None:
        with session_scope() as session:
            job = session.get(ResearchJobRow, research_id)
            if job is None:
                return None
            return state_from_rows(
                job=job,
                tasks=self._children(session, ResearchTaskRow, research_id),
                sources=self._children(session, SourceRow, research_id),
                documents=self._children(session, DocumentRow, research_id),
                passages=self._children(session, PassageRow, research_id),
                entities=self._children(session, EntityRow, research_id),
                claims=self._children(session, ClaimRow, research_id),
                evidence=self._children(session, EvidenceRow, research_id),
                contradictions=self._children(session, ContradictionRow, research_id),
            )

    def save(self, state: ResearchState) -> None:
        with session_scope() as session:
            self._delete_children(session, state.research_id)
            existing_job = session.get(ResearchJobRow, state.research_id)
            if existing_job is not None:
                session.delete(existing_job)
                session.flush()

            job_row = job_row_from_state(state)
            job_row.updated_at = utcnow()
            session.add(job_row)
            session.flush()

            session.add_all(task_rows_from_state(state))
            session.add_all(source_rows_from_state(state))
            session.add_all(document_rows_from_state(state))
            session.add_all(passage_rows_from_state(state))
            session.add_all(entity_rows_from_state(state))
            session.add_all(claim_rows_from_state(state))
            session.add_all(evidence_rows_from_state(state))
            session.add_all(contradiction_rows_from_state(state))

    @staticmethod
    def _children(session, row_type, research_id: str) -> list:
        return list(
            session.scalars(
                select(row_type).where(row_type.job_id == research_id)
            ).all()
        )

    @staticmethod
    def _delete_children(session, research_id: str) -> None:
        for row_type in _CHILD_ROW_TYPES:
            session.execute(delete(row_type).where(row_type.job_id == research_id))


class InMemoryJobRepository:
    """Test double: stores deep copies of states keyed by research id."""

    def __init__(self) -> None:
        self._states: dict[str, ResearchState] = {}

    def create(
        self,
        request: ResearchRequest,
        owner_user_id: str | None = None,
        owner_session_id: str | None = None,
    ) -> ResearchState:
        state = _new_state(request, owner_user_id, owner_session_id)
        self.save(state)
        return state

    def get(self, research_id: str) -> ResearchState | None:
        stored = self._states.get(research_id)
        return stored.model_copy(deep=True) if stored is not None else None

    def save(self, state: ResearchState) -> None:
        self._states[state.research_id] = state.model_copy(deep=True)
