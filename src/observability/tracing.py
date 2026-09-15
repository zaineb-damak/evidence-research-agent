"""Lightweight tracing around pipeline stages (§19).

Wraps a stage in an OpenTelemetry span so latency per stage is inspectable. The
tracer is a no-op unless an OTel SDK/exporter is configured, so this is always
safe to call and adds nothing in tests. Langfuse LLM-level tracing is attached
at the provider boundary when keys are present.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager

from opentelemetry import trace

TRACER_NAME = "evidence-research-agent"
STAGE_NAME_ATTRIBUTE = "research.stage"

_tracer = trace.get_tracer(TRACER_NAME)


@contextmanager
def stage_span(stage_name: str) -> Iterator[None]:
    with _tracer.start_as_current_span(stage_name) as span:
        span.set_attribute(STAGE_NAME_ATTRIBUTE, stage_name)
        yield


def traced_stage[ResultType](stage_name: str, operation: Callable[[], ResultType]) -> ResultType:
    with stage_span(stage_name):
        return operation()
