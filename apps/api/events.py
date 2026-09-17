"""Server-sent events for live research progress.

`GET /api/research/{id}/events` (apps/api/main.py) streams `ProgressEvent`s to
an authenticated, owning caller. `stream_progress` always yields a SNAPSHOT
event first (the currently persisted status + progress_detail, so a client
connecting mid-run or after completion is never stuck waiting); if the
snapshot is already terminal it yields the terminal event and returns
immediately (no Redis subscription needed), otherwise it subscribes to the
job's channel and forwards events, stopping after a DONE/ERROR event.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from src.config import Settings
from src.models.progress import (
    TERMINAL_JOB_STATUSES,
    JobProgressSnapshot,
    ProgressEvent,
    ProgressEventType,
)
from src.models.schemas import ResearchStatus
from src.realtime.pubsub import subscribe_to_progress

SSE_MEDIA_TYPE = "text/event-stream"

# The two ProgressEventTypes that end a stream.
_STREAM_TERMINAL_EVENT_TYPES = (ProgressEventType.DONE, ProgressEventType.ERROR)


def format_sse(event_name: str, data: str) -> str:
    return f"event: {event_name}\ndata: {data}\n\n"


def _terminal_event_type(status: ResearchStatus) -> ProgressEventType:
    return ProgressEventType.ERROR if status == ResearchStatus.FAILED else ProgressEventType.DONE


def _snapshot_event(snapshot: JobProgressSnapshot) -> ProgressEvent:
    return ProgressEvent(
        research_id=snapshot.research_id,
        event_type=ProgressEventType.SNAPSHOT,
        stage=None,
        status=snapshot.status,
        message=snapshot.error or "",
        detail=snapshot.progress_detail,
        emitted_at=snapshot.updated_at,
    )


def _terminal_event(snapshot: JobProgressSnapshot) -> ProgressEvent:
    return ProgressEvent(
        research_id=snapshot.research_id,
        event_type=_terminal_event_type(snapshot.status),
        stage=None,
        status=snapshot.status,
        message=snapshot.error or "",
        detail=snapshot.progress_detail,
        emitted_at=snapshot.updated_at,
    )


async def stream_progress(
    snapshot: JobProgressSnapshot, settings: Settings
) -> AsyncIterator[str]:
    snapshot_event = _snapshot_event(snapshot)
    yield format_sse(snapshot_event.event_type.value, snapshot_event.model_dump_json())

    if snapshot.status in TERMINAL_JOB_STATUSES:
        terminal_event = _terminal_event(snapshot)
        yield format_sse(terminal_event.event_type.value, terminal_event.model_dump_json())
        return

    async for event in subscribe_to_progress(snapshot.research_id, settings):
        yield format_sse(event.event_type.value, event.model_dump_json())
        if event.event_type in _STREAM_TERMINAL_EVENT_TYPES:
            break
