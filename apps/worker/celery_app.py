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
from celery.signals import setup_logging, worker_ready
from langgraph.checkpoint.postgres import PostgresSaver

from apps.worker.progress import build_progress_sink
from src.clock import MILLISECONDS_PER_SECOND
from src.config import get_settings
from src.db.repository import PostgresJobRepository
from src.llm.caching import configure_llm_cache
from src.models.schemas import ResearchStatus
from src.observability.langfuse import langfuse_callbacks
from src.observability.logging import (
    RESEARCH_ID_FIELD,
    USER_ID_FIELD,
    bind_request_context,
    clear_request_context,
    configure_logging,
    get_logger,
)
from src.observability.metrics import (
    RESEARCH_JOBS_IN_PROGRESS,
    observe_research_job,
    start_worker_metrics_server,
)
from src.workflows.checkpoint import compose_thread_id
from src.workflows.deps import build_deps
from src.workflows.progress_emitter import build_terminal_event
from src.workflows.research import run_pipeline

RESEARCH_TASK_NAME = "research.run"
JOB_FAILED_EVENT = "research_task_failed"
SECONDS_PER_MILLISECOND = 1 / MILLISECONDS_PER_SECOND

# macOS aborts a forked child that touches an Objective-C framework (which
# httpx/openai do via system-proxy detection), crashing Celery's default
# prefork pool with SIGABRT. The workload is I/O-bound, so a thread pool is both
# the fix and a good fit. Linux keeps the default prefork pool. A `--pool` CLI
# flag still overrides this.
MACOS_PLATFORM = "darwin"
THREAD_POOL = "threads"

# kombu leaves the broker socket with no timeout. On SIGTERM an idle worker was
# observed blocked in that socket read indefinitely, never reaching its shutdown
# check, so it sat out the whole Kubernetes grace period and was then killed.
# Kept well above kombu's 1s BRPOP poll so normal waits never trip it.
BROKER_SOCKET_TIMEOUT_SECONDS = 10
SOCKET_TIMEOUT_OPTION = "socket_timeout"

logger = get_logger(__name__)
settings = get_settings()
celery_app = Celery("research", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.broker_transport_options = {SOCKET_TIMEOUT_OPTION: BROKER_SOCKET_TIMEOUT_SECONDS}

# Wire LangChain's global LLM cache once per worker process.
configure_llm_cache(settings)

if sys.platform == MACOS_PLATFORM:
    celery_app.conf.worker_pool = THREAD_POOL


@setup_logging.connect
def configure_worker_logging(**_kwargs) -> None:
    """Keep Celery from installing its own handlers so all output stays JSON.

    Connecting to this signal at all disables Celery's logging setup; we then
    install the same structlog configuration the API uses.
    """
    configure_logging(settings)


@worker_ready.connect
def start_metrics_endpoint(**_kwargs) -> None:
    """Serve /metrics from the worker once it is accepting tasks.

    Bound in the main worker process, which is also where tasks execute: the
    container runs the thread pool (see the container command), so there are no
    prefork children whose counters would be invisible here.
    """
    start_worker_metrics_server(settings)


@celery_app.task(name=RESEARCH_TASK_NAME)
def run_research_task(research_id: str) -> dict:
    repository = PostgresJobRepository()
    state = repository.get(research_id)
    if state is None:
        return {"research_id": research_id, "status": "not_found"}

    clear_request_context()
    bind_request_context(
        **{RESEARCH_ID_FIELD: research_id, USER_ID_FIELD: state.owner_user_id}
    )
    RESEARCH_JOBS_IN_PROGRESS.inc()

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
            logger.exception(JOB_FAILED_EVENT)
            state.status = ResearchStatus.FAILED
            state.error = f"{type(error).__name__}: {error}"
        finally:
            state.cost.latency_ms = int((time.time() - started_at) * MILLISECONDS_PER_SECOND)
            repository.save(state)
            # Guarantees a terminal event reaches subscribers even on a hard
            # crash (an exception above, or one save() itself never raised).
            progress_sink(build_terminal_event(state))
            RESEARCH_JOBS_IN_PROGRESS.dec()
            observe_research_job(
                status=state.status,
                duration_seconds=state.cost.latency_ms * SECONDS_PER_MILLISECOND,
                cost_usd=state.cost.usd,
                tokens_in=state.cost.tokens_in,
                tokens_out=state.cost.tokens_out,
            )
            clear_request_context()

    return {"research_id": state.research_id, "status": state.status}
