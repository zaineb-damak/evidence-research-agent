"""Prometheus metrics for the API and the worker.

Both processes expose the same exposition format: the API serves it on
`GET /metrics` (see apps/api/routes_health.py), the worker — which has no HTTP
server of its own — opens a small one on `worker_metrics_port`.

Each container runs a single process (scale with replicas, not with in-process
workers), so the default single-process registry is correct and no multiprocess
collector directory is needed.
"""

from __future__ import annotations

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
    start_http_server,
)

from src.config import Settings, get_settings

# Label names — one home for the metric vocabulary.
METHOD_LABEL = "method"
ROUTE_LABEL = "route"
STATUS_LABEL = "status"
DIRECTION_LABEL = "direction"
SERVICE_LABEL = "service"
ENVIRONMENT_LABEL = "environment"
VERSION_LABEL = "version"

TOKENS_IN_DIRECTION = "in"
TOKENS_OUT_DIRECTION = "out"

# Web request latencies: sub-second buckets for the JSON routes, with a long
# tail because the SSE stream route stays open for the life of a research job.
HTTP_LATENCY_BUCKETS_SECONDS = (0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0)

# Research jobs run for minutes, not milliseconds — hence a coarser scale.
JOB_DURATION_BUCKETS_SECONDS = (5.0, 15.0, 30.0, 60.0, 120.0, 300.0, 600.0, 1800.0)

APP_INFO = Gauge(
    "app_info",
    "Build and deployment identity of this process (always 1).",
    [SERVICE_LABEL, ENVIRONMENT_LABEL, VERSION_LABEL],
)

HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "HTTP requests handled, by method, route template and status code.",
    [METHOD_LABEL, ROUTE_LABEL, STATUS_LABEL],
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "http_request_duration_seconds",
    "Wall-clock time to produce an HTTP response.",
    [METHOD_LABEL, ROUTE_LABEL],
    buckets=HTTP_LATENCY_BUCKETS_SECONDS,
)

RESEARCH_JOBS_TOTAL = Counter(
    "research_jobs_total",
    "Research jobs that reached a terminal state, by status.",
    [STATUS_LABEL],
)

RESEARCH_JOBS_IN_PROGRESS = Gauge(
    "research_jobs_in_progress",
    "Research jobs currently executing in this worker.",
)

RESEARCH_JOB_DURATION_SECONDS = Histogram(
    "research_job_duration_seconds",
    "End-to-end pipeline duration for a research job.",
    buckets=JOB_DURATION_BUCKETS_SECONDS,
)

RESEARCH_JOB_COST_USD_TOTAL = Counter(
    "research_job_cost_usd_total",
    "Cumulative LLM spend attributed to completed research jobs.",
)

RESEARCH_JOB_TOKENS_TOTAL = Counter(
    "research_job_tokens_total",
    "Cumulative LLM tokens attributed to completed research jobs.",
    [DIRECTION_LABEL],
)


def set_app_info(settings: Settings | None = None) -> None:
    settings = settings or get_settings()
    APP_INFO.labels(
        **{
            SERVICE_LABEL: settings.service_name,
            ENVIRONMENT_LABEL: settings.environment.value,
            VERSION_LABEL: settings.release_version,
        }
    ).set(1)


def observe_http_request(
    method: str, route: str, status_code: int, duration_seconds: float
) -> None:
    HTTP_REQUESTS_TOTAL.labels(
        **{METHOD_LABEL: method, ROUTE_LABEL: route, STATUS_LABEL: str(status_code)}
    ).inc()
    HTTP_REQUEST_DURATION_SECONDS.labels(
        **{METHOD_LABEL: method, ROUTE_LABEL: route}
    ).observe(duration_seconds)


def observe_research_job(
    status: str, duration_seconds: float, cost_usd: float, tokens_in: int, tokens_out: int
) -> None:
    RESEARCH_JOBS_TOTAL.labels(**{STATUS_LABEL: status}).inc()
    RESEARCH_JOB_DURATION_SECONDS.observe(duration_seconds)
    RESEARCH_JOB_COST_USD_TOTAL.inc(cost_usd)
    RESEARCH_JOB_TOKENS_TOTAL.labels(**{DIRECTION_LABEL: TOKENS_IN_DIRECTION}).inc(tokens_in)
    RESEARCH_JOB_TOKENS_TOTAL.labels(**{DIRECTION_LABEL: TOKENS_OUT_DIRECTION}).inc(tokens_out)


def render_latest() -> tuple[bytes, str]:
    """The current metric values plus the content type Prometheus expects."""
    return generate_latest(), CONTENT_TYPE_LATEST


def start_worker_metrics_server(settings: Settings | None = None) -> None:
    """Expose /metrics from the worker process so Prometheus can scrape it."""
    settings = settings or get_settings()
    if not settings.metrics_enabled:
        return
    set_app_info(settings)
    start_http_server(settings.worker_metrics_port)
