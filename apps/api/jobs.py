"""Job lookup with ownership enforcement.

Kept apart from the route handlers (CLAUDE.md rule 6). Raises 404 for an unknown
job and 403 when the authenticated caller does not own it.
"""

from __future__ import annotations

from fastapi import HTTPException, status

from apps.api.auth import AuthContext
from src.db.repository import JobRepository
from src.exceptions import JobAccessDeniedError, JobNotFoundError
from src.models.progress import JobProgressSnapshot
from src.models.schemas import ResearchState


def _enforce_ownership(owner_user_id: str | None, auth: AuthContext) -> None:
    if owner_user_id is not None and owner_user_id != auth.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=JobAccessDeniedError.MESSAGE
        )


def require_owned_job(
    repository: JobRepository, research_id: str, auth: AuthContext
) -> ResearchState:
    state = repository.get(research_id)
    if state is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=JobNotFoundError.MESSAGE)
    _enforce_ownership(state.owner_user_id, auth)
    return state


def require_owned_job_snapshot(
    repository: JobRepository, research_id: str, auth: AuthContext
) -> JobProgressSnapshot:
    snapshot = repository.get_progress_snapshot(research_id)
    if snapshot is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=JobNotFoundError.MESSAGE)
    _enforce_ownership(snapshot.owner_user_id, auth)
    return snapshot
