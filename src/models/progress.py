"""Live-progress event model.

`ProgressEvent`s are emitted from inside LangGraph nodes
(src/workflows/progress_emitter.py) and forwarded by `run_pipeline`
(src/workflows/research.py) to whatever sink the caller wires up — in
production, the worker's Redis-backed sink (apps/worker/progress.py).
`JobProgressSnapshot` is the cheap, column-only persisted view a client reads
on first connect (GET /api/research/{id}/events, apps/api/events.py).
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from src.clock import utcnow
from src.models.schemas import ResearchStatus


class ProgressEventType(StrEnum):
    SNAPSHOT = "snapshot"
    STAGE_STARTED = "stage_started"
    STAGE_COMPLETED = "stage_completed"
    SUBSTEP = "substep"
    DONE = "done"
    ERROR = "error"


class ProgressEvent(BaseModel):
    """One update in a research job's live-progress stream."""

    research_id: str
    event_type: ProgressEventType
    stage: str | None = None
    status: ResearchStatus
    message: str = ""
    detail: dict[str, Any] = Field(default_factory=dict)
    emitted_at: datetime = Field(default_factory=utcnow)


class JobProgressSnapshot(BaseModel):
    """The persisted view of a job's progress, for a client's first connect."""

    research_id: str
    owner_user_id: str | None = None
    status: ResearchStatus
    error: str | None = None
    progress_detail: dict[str, Any] = Field(default_factory=dict)
    updated_at: datetime


TERMINAL_JOB_STATUSES = frozenset({ResearchStatus.COMPLETED, ResearchStatus.FAILED})

# What a progress emitter/sink hands events to — a plain callback so
# src/workflows/research.py and the agents stay decoupled from any particular
# transport (Redis pub/sub, an in-test list, etc).
ProgressEventSink = Callable[[ProgressEvent], None]
