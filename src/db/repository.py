"""Job repository: the durable store of research jobs and their evidence.

`PostgresJobRepository` is the production system of record. `InMemoryJobRepository`
is a test double with identical behavior, so the API and worker can be exercised
without a live database. Both satisfy the `JobRepository` protocol.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol, runtime_checkable

from sqlalchemy import delete, select, update

from src.clock import utcnow
from src.db.base import session_scope
from src.db.mappers import (
    claim_rows_from_state,
    contradiction_rows_from_state,
    document_rows_from_state,
    entity_rows_from_state,
    evidence_rows_from_state,
    job_list_item_from_row,
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
from src.models.progress import JobProgressSnapshot
from src.models.schemas import (
    ResearchJobListItem,
    ResearchRequest,
    ResearchState,
    ResearchStatus,
)

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

# Session history (`GET /api/research`) is capped, not paginated, in v1.
JOB_LIST_MAX_RESULTS = 50


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

    def list_by_user(self, user_id: str) -> list[ResearchJobListItem]: ...

    def update_progress(
        self,
        research_id: str,
        status: ResearchStatus | None,
        detail: dict[str, Any] | None,
        error: str | None,
    ) -> None: ...

    def get_progress_snapshot(self, research_id: str) -> JobProgressSnapshot | None: ...


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

    def list_by_user(self, user_id: str) -> list[ResearchJobListItem]:
        # Deliberately not the 8-child-table `get()` path: history only needs
        # title/status/timestamps, so this is a single column-projected query
        # against `research_jobs` alone. Jobs with owner_user_id IS NULL
        # (legacy/anonymous) never match and are therefore excluded from every
        # user's history automatically.
        with session_scope() as session:
            rows = session.execute(
                select(
                    ResearchJobRow.id,
                    ResearchJobRow.question,
                    ResearchJobRow.status,
                    ResearchJobRow.depth,
                    ResearchJobRow.error,
                    ResearchJobRow.created_at,
                    ResearchJobRow.updated_at,
                )
                .where(ResearchJobRow.owner_user_id == user_id)
                .order_by(ResearchJobRow.created_at.desc())
                .limit(JOB_LIST_MAX_RESULTS)
            ).all()
            return [job_list_item_from_row(row) for row in rows]

    def update_progress(
        self,
        research_id: str,
        status: ResearchStatus | None,
        detail: dict[str, Any] | None,
        error: str | None,
    ) -> None:
        # A targeted single-column UPDATE — no ORM row load, no child-table
        # cascade. This is the cheap write path called once per progress
        # event; the expensive full `save()` (sources/claims/passages/...)
        # stays reserved for the end of the run.
        values: dict[str, Any] = {"updated_at": utcnow()}
        if status is not None:
            values["status"] = status.value
        if detail is not None:
            values["progress_detail"] = detail
        if error is not None:
            values["error"] = error
        with session_scope() as session:
            session.execute(
                update(ResearchJobRow)
                .where(ResearchJobRow.id == research_id)
                .values(**values)
            )

    def get_progress_snapshot(self, research_id: str) -> JobProgressSnapshot | None:
        with session_scope() as session:
            row = session.execute(
                select(
                    ResearchJobRow.id,
                    ResearchJobRow.owner_user_id,
                    ResearchJobRow.status,
                    ResearchJobRow.error,
                    ResearchJobRow.progress_detail,
                    ResearchJobRow.updated_at,
                ).where(ResearchJobRow.id == research_id)
            ).first()
            if row is None:
                return None
            return JobProgressSnapshot(
                research_id=row.id,
                owner_user_id=row.owner_user_id,
                status=ResearchStatus(row.status),
                error=row.error,
                progress_detail=row.progress_detail or {},
                updated_at=row.updated_at,
            )

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
    """Test double: stores deep copies of states keyed by research id.

    `ResearchState` itself carries no timestamps (those are a persistence-layer
    concept), so created_at/updated_at are side-tracked here to support
    `list_by_user` with the same shape the Postgres repository returns.
    """

    def __init__(self) -> None:
        self._states: dict[str, ResearchState] = {}
        self._created_at: dict[str, datetime] = {}
        self._updated_at: dict[str, datetime] = {}
        # Side-tracked like created_at/updated_at above: ResearchState carries
        # no progress_detail field of its own (that's a persistence-layer
        # concept, mirroring the Postgres column of the same name).
        self._progress_detail: dict[str, dict[str, Any]] = {}

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
        now = utcnow()
        self._created_at.setdefault(state.research_id, now)
        self._updated_at[state.research_id] = now
        self._states[state.research_id] = state.model_copy(deep=True)

    def list_by_user(self, user_id: str) -> list[ResearchJobListItem]:
        # Jobs with owner_user_id None (legacy/anonymous) never match and are
        # therefore excluded from every user's history automatically. Mirrors
        # SQL NULL semantics (`owner_user_id = :user_id` never matches a NULL
        # column, and a NULL parameter would never match anything either) even
        # though a real caller's user_id is never None in practice.
        items = [
            ResearchJobListItem(
                research_id=state.research_id,
                question=state.original_question,
                status=state.status,
                depth=state.depth,
                error=state.error,
                created_at=self._created_at[state.research_id],
                updated_at=self._updated_at[state.research_id],
            )
            for state in self._states.values()
            if user_id is not None and state.owner_user_id == user_id
        ]
        items.sort(key=lambda item: item.created_at, reverse=True)
        return items[:JOB_LIST_MAX_RESULTS]

    def update_progress(
        self,
        research_id: str,
        status: ResearchStatus | None,
        detail: dict[str, Any] | None,
        error: str | None,
    ) -> None:
        state = self._states.get(research_id)
        if state is None:
            return
        if status is not None:
            state.status = status
        if error is not None:
            state.error = error
        if detail is not None:
            self._progress_detail[research_id] = detail
        self._updated_at[research_id] = utcnow()

    def get_progress_snapshot(self, research_id: str) -> JobProgressSnapshot | None:
        state = self._states.get(research_id)
        if state is None:
            return None
        return JobProgressSnapshot(
            research_id=state.research_id,
            owner_user_id=state.owner_user_id,
            status=state.status,
            error=state.error,
            progress_detail=self._progress_detail.get(research_id, {}),
            updated_at=self._updated_at[research_id],
        )
