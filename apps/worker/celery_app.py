"""Celery worker — the production execution path.

The API persists a queued job to Postgres and enqueues its id here. The worker
loads the job, runs the LangGraph pipeline (with a Postgres-backed checkpointer
so an interrupted run resumes), persists the final state, and records latency.

Run: `celery -A apps.worker.celery_app worker --loglevel=info`
"""

from __future__ import annotations

import sys
import time

from celery import Celery
from celery.utils.log import get_task_logger
from langgraph.checkpoint.postgres import PostgresSaver

from apps.worker.progress import build_progress_sink
from src.config import get_settings
from src.db.repository import PostgresJobRepository
from src.llm.caching import configure_llm_cache
from src.models.schemas import ResearchStatus
from src.observability.langfuse import langfuse_callbacks
from src.workflows.checkpoint import compose_thread_id
from src.workflows.deps import build_deps
from src.workflows.progress_emitter import build_terminal_event
from src.workflows.research import run_pipeline

MILLISECONDS_PER_SECOND = 1000
RESEARCH_TASK_NAME = "research.run"

# macOS aborts a forked child that touches an Objective-C framework (which
# httpx/openai do via system-proxy detection), crashing Celery's default
# prefork pool with SIGABRT. The workload is I/O-bound, so a thread pool is both
# the fix and a good fit. Linux keeps the default prefork pool. A `--pool` CLI
# flag still overrides this.
MACOS_PLATFORM = "darwin"
THREAD_POOL = "threads"

logger = get_task_logger(__name__)
settings = get_settings()
celery_app = Celery("research", broker=settings.redis_url, backend=settings.redis_url)

# Wire LangChain's global LLM cache once per worker process.
configure_llm_cache(settings)

if sys.platform == MACOS_PLATFORM:
    celery_app.conf.worker_pool = THREAD_POOL


@celery_app.task(name=RESEARCH_TASK_NAME)
def run_research_task(research_id: str) -> dict:
    repository = PostgresJobRepository()
    state = repository.get(research_id)
    if state is None:
        return {"research_id": research_id, "status": "not_found"}

    started_at = time.time()
    # LangGraph's Postgres checkpointer persists node-level progress so a crashed
    # worker resumes from the last completed node instead of restarting.
    thread_id = compose_thread_id(
        settings.checkpoint_thread_scope,
        state.research_id,
        user_id=state.owner_user_id,
        session_id=state.owner_session_id,
    )
    callbacks = langfuse_callbacks(settings)
    progress_sink = build_progress_sink(repository, settings)
    with PostgresSaver.from_conn_string(settings.postgres_libpq_dsn) as checkpointer:
        checkpointer.setup()
        deps = build_deps(state.source_types, settings)
        try:
            run_pipeline(
                state,
                deps,
                checkpointer=checkpointer,
                thread_id=thread_id,
                callbacks=callbacks,
                on_progress_event=progress_sink,
            )
        except Exception as error:  # noqa: BLE001 — job-level boundary
            # Log the full traceback so failures are visible in the worker
            # console, not just stored as a message on the job.
            logger.exception("research task failed for %s", research_id)
            state.status = ResearchStatus.FAILED
            state.error = f"{type(error).__name__}: {error}"
        finally:
            state.cost.latency_ms = int((time.time() - started_at) * MILLISECONDS_PER_SECOND)
            repository.save(state)
            # Guarantees a terminal event reaches subscribers even on a hard
            # crash (an exception above, or one save() itself never raised).
            progress_sink(build_terminal_event(state))

    return {"research_id": state.research_id, "status": state.status}
