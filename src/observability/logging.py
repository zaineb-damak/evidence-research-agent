"""Structured logging for every process in the system.

structlog renders one JSON object per line in deployed environments (what a
cluster log collector parses) and colorized key/value lines locally. Call
`configure_logging` once at process startup — the API does it at import time,
the worker on Celery's `setup_logging` signal — then use `get_logger(__name__)`.

Logs emitted by libraries (uvicorn, celery, sqlalchemy, neo4j) are routed
through the same formatter via `ProcessorFormatter`, so a deployment never has
a mix of JSON and plain lines on stdout.

Correlation ids live in structlog's contextvars rather than in call signatures:
`bind_request_context` binds them once per request/task and every line emitted
downstream carries them automatically.
"""

from __future__ import annotations

import logging
import sys
from collections.abc import MutableMapping
from typing import Any

import structlog

from src.config import LogFormat, LogLevel, Settings, get_settings

# Log record keys. Named so the field vocabulary has one home and dashboards
# can rely on it.
SERVICE_FIELD = "service"
ENVIRONMENT_FIELD = "environment"
VERSION_FIELD = "version"
REQUEST_ID_FIELD = "request_id"
RESEARCH_ID_FIELD = "research_id"
USER_ID_FIELD = "user_id"

STDLIB_LEVEL_BY_LOG_LEVEL: dict[LogLevel, int] = {
    LogLevel.DEBUG: logging.DEBUG,
    LogLevel.INFO: logging.INFO,
    LogLevel.WARNING: logging.WARNING,
    LogLevel.ERROR: logging.ERROR,
}

# uvicorn's own access log duplicates the access line emitted by
# apps/api/middleware.py (which also carries the request id), so it is quieted
# rather than disabled — its startup/error lines are still worth having.
QUIETED_LOGGER_LEVELS: dict[str, int] = {
    "uvicorn.access": logging.WARNING,
}


def _service_context_processor(settings: Settings) -> Any:
    """Stamp service/environment/version onto every record."""

    def add_service_context(
        _logger: Any, _method_name: str, event_dict: MutableMapping[str, Any]
    ) -> MutableMapping[str, Any]:
        event_dict[SERVICE_FIELD] = settings.service_name
        event_dict[ENVIRONMENT_FIELD] = settings.environment.value
        event_dict[VERSION_FIELD] = settings.release_version
        return event_dict

    return add_service_context


def configure_logging(settings: Settings | None = None) -> None:
    settings = settings or get_settings()

    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
        _service_context_processor(settings),
    ]

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    renderer = (
        structlog.processors.JSONRenderer()
        if settings.log_format is LogFormat.JSON
        else structlog.dev.ConsoleRenderer()
    )
    formatter = structlog.stdlib.ProcessorFormatter(
        # Applied to records from libraries that never touched structlog, so
        # their lines carry the same fields as ours.
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.format_exc_info,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(STDLIB_LEVEL_BY_LOG_LEVEL[settings.log_level])

    for logger_name, level in QUIETED_LOGGER_LEVELS.items():
        logging.getLogger(logger_name).setLevel(level)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    return structlog.stdlib.get_logger(name)


def bind_request_context(**fields: str | None) -> None:
    """Bind correlation ids for the current request/task, dropping empty ones."""
    structlog.contextvars.bind_contextvars(
        **{key: value for key, value in fields.items() if value is not None}
    )


def clear_request_context() -> None:
    structlog.contextvars.clear_contextvars()
