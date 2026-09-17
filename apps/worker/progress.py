"""Wire ProgressEvents from the pipeline into persistence + pub/sub.

`build_progress_sink` returns the `ProgressEventSink` the worker passes into
`run_pipeline(on_progress_event=...)`: each event first updates the cheap
`research_jobs.status`/`progress_detail` columns, then publishes it on the
job's Redis channel so any subscribed SSE connections see it live.
"""

from __future__ import annotations

from src.config import Settings
from src.db.repository import JobRepository
from src.models.progress import ProgressEvent, ProgressEventSink, ProgressEventType
from src.realtime.pubsub import publish_progress_event


def build_progress_sink(repository: JobRepository, settings: Settings) -> ProgressEventSink:
    def sink(event: ProgressEvent) -> None:
        is_error_event = event.event_type == ProgressEventType.ERROR
        repository.update_progress(
            event.research_id,
            status=event.status,
            detail=event.detail,
            error=event.message if is_error_event else None,
        )
        publish_progress_event(event, settings)

    return sink
