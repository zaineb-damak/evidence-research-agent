"""Make a connector's fail-open search failure observable.

Connectors return no results instead of raising, so one unavailable source
never sinks a run. Without this, a rate-limited or misconfigured connector
silently drops its source type from every report; with it, each failure is a
structured warning and a `source_connector_failures_total` increment.
"""

from __future__ import annotations

import httpx

from src.observability.logging import get_logger
from src.observability.metrics import observe_connector_failure

CONNECTOR_SEARCH_FAILED_EVENT = "source_connector_search_failed"

logger = get_logger(__name__)


def failure_reason(error: Exception) -> str:
    """A low-cardinality label: the HTTP status when there is one, else the error type."""
    if isinstance(error, httpx.HTTPStatusError):
        return str(error.response.status_code)
    return type(error).__name__


def record_connector_failure(connector: str, error: Exception) -> None:
    reason = failure_reason(error)
    observe_connector_failure(connector, reason)
    logger.warning(
        CONNECTOR_SEARCH_FAILED_EVENT, connector=connector, reason=reason, error=str(error)
    )
