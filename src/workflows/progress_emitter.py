"""Emit ProgressEvents from inside LangGraph nodes.

`get_stream_writer()` is always safe to call: LangGraph hands back a no-op
writer unless the graph is actually being run with `stream_mode` including
`"custom"` (see `run_pipeline`, src/workflows/research.py). Only this module
and src/workflows/nodes.py know about LangGraph streaming — the agents
(src/agents/*) take plain callbacks and stay LangGraph-agnostic.
"""

from __future__ import annotations

from langgraph.config import get_stream_writer

from src.models.progress import ProgressEvent, ProgressEventType
from src.models.schemas import NodeName, ResearchState, ResearchStatus

# The ResearchStatus a stage represents the moment it *starts* (before the node
# has run and set its own "status" return value). SYNTHESIZE maps to
# SYNTHESIZING even though the persisted job row jumps straight from VERIFYING
# to COMPLETED once synthesis finishes — this progress stream is the only place
# SYNTHESIZING is actually observed.
STAGE_STARTED_STATUS: dict[NodeName, ResearchStatus] = {
    NodeName.PLAN: ResearchStatus.PLANNING,
    NodeName.SEARCH: ResearchStatus.SEARCHING,
    NodeName.EXTRACT: ResearchStatus.EXTRACTING,
    NodeName.SCORE: ResearchStatus.RESOLVING,
    NodeName.VERIFY: ResearchStatus.VERIFYING,
    NodeName.SYNTHESIZE: ResearchStatus.SYNTHESIZING,
}

STAGE_STARTED_MESSAGE_TEMPLATE = "Started {stage}"
TERMINAL_DONE_MESSAGE = "Research complete"


def emit_stage_started(research_id: str, stage: NodeName) -> None:
    """Signal that `stage` has just begun running."""
    stream_writer = get_stream_writer()
    stream_writer(
        ProgressEvent(
            research_id=research_id,
            event_type=ProgressEventType.STAGE_STARTED,
            stage=stage.value,
            status=STAGE_STARTED_STATUS[stage],
            message=STAGE_STARTED_MESSAGE_TEMPLATE.format(stage=stage.value),
        )
    )


def emit_substep(
    research_id: str,
    stage: NodeName,
    message: str,
    detail: dict | None = None,
) -> None:
    """Signal fine-grained progress within a still-running stage."""
    stream_writer = get_stream_writer()
    stream_writer(
        ProgressEvent(
            research_id=research_id,
            event_type=ProgressEventType.SUBSTEP,
            stage=stage.value,
            status=STAGE_STARTED_STATUS[stage],
            message=message,
            detail=detail or {},
        )
    )


def build_terminal_event(state: ResearchState) -> ProgressEvent:
    """Build the run's final DONE/ERROR event.

    Pure — called after `run_pipeline` has already returned or raised, outside
    any Pregel runtime context, so there is no stream writer to call here.
    """
    event_type = ProgressEventType.ERROR if state.error else ProgressEventType.DONE
    return ProgressEvent(
        research_id=state.research_id,
        event_type=event_type,
        stage=None,
        status=state.status,
        message=state.error or TERMINAL_DONE_MESSAGE,
    )
