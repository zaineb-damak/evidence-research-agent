"""Job lookup with ownership enforcement.

Kept apart from the route handlers (CLAUDE.md rule 6). Raises 404 for an unknown
job and 403 when the authenticated caller does not own it.
"""

from __future__ import annotations

from fastapi import HTTPException, status

from apps.api.auth import AuthContext
from src.db.repository import JobRepository
from src.exceptions import JobAccessDeniedError, JobNotFoundError
from src.models.schemas import ResearchState


def require_owned_job(
    repository: JobRepository, research_id: str, auth: AuthContext
) -> ResearchState:
    state = repository.get(research_id)
    if state is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=JobNotFoundError.MESSAGE)
    if state.owner_user_id is not None and state.owner_user_id != auth.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=JobAccessDeniedError.MESSAGE
        )
    return state
