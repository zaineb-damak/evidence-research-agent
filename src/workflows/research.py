"""Research pipeline as a LangGraph StateGraph.

Each stage (plan → search → extract → score → verify → synthesize) is a graph
node operating on the shared ResearchState (nodes live in src/workflows/nodes.py).
A conditional edge after search skips straight to synthesis when no passages were
found. The graph is compiled with a checkpointer so an interrupted run resumes
from the last completed node.

Retrieval and the evidence graph are backed by injected stores:
- `passage_index` (Postgres FTS keyword + Qdrant vectors) owns passage storage,
- `graph_store` (Neo4j) receives the evidence graph at synthesis time.

`run_pipeline` keeps a back-compatible signature; the checkpoint thread id and
tracing callbacks are optional so existing callers and tests are unaffected.
"""

from __future__ import annotations

from enum import StrEnum
from functools import partial
from typing import Any

from langchain_core.callbacks import BaseCallbackHandler
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from src.models.progress import ProgressEvent, ProgressEventSink, ProgressEventType
from src.models.schemas import CostMeter, NodeName, ResearchState, ResearchStatus, WorkflowRoute
from src.workflows.nodes import (
    Deps,
    extract_node,
    plan_node,
    score_node,
    search_node,
    synthesize_node,
    verify_node,
)
from src.workflows.routing import route_after_search

# Re-exported so existing imports (tests, deps assembly) keep working.
__all__ = ["Deps", "NodeName", "build_state_graph", "compile_graph", "run_pipeline"]

STAGE_COMPLETED_MESSAGE_TEMPLATE = "Completed {stage}"

# Fields on a node's partial-state-update dict that are lists we summarize into
# counts for STAGE_COMPLETED event `detail`, instead of forwarding the (large)
# lists themselves over the wire.
NODE_UPDATE_LIST_FIELDS = (
    "research_tasks",
    "sources",
    "documents",
    "passages",
    "entities",
    "evidence",
    "claims",
    "contradictions",
)


class GraphStreamMode(StrEnum):
    """`stream_mode` values `run_pipeline` requests from `compiled_graph.stream`."""

    UPDATES = "updates"
    CUSTOM = "custom"


def build_state_graph(deps: Deps) -> StateGraph:
    graph = StateGraph(ResearchState)
    graph.add_node(NodeName.PLAN, partial(plan_node, deps=deps))
    graph.add_node(NodeName.SEARCH, partial(search_node, deps=deps))
    graph.add_node(NodeName.EXTRACT, partial(extract_node, deps=deps))
    graph.add_node(NodeName.SCORE, partial(score_node, deps=deps))
    graph.add_node(NodeName.VERIFY, partial(verify_node, deps=deps))
    graph.add_node(NodeName.SYNTHESIZE, partial(synthesize_node, deps=deps))

    graph.add_edge(START, NodeName.PLAN)
    graph.add_edge(NodeName.PLAN, NodeName.SEARCH)
    graph.add_conditional_edges(
        NodeName.SEARCH,
        route_after_search,
        {
            WorkflowRoute.HAS_PASSAGES: NodeName.EXTRACT,
            WorkflowRoute.NO_PASSAGES: NodeName.SYNTHESIZE,
        },
    )
    graph.add_edge(NodeName.EXTRACT, NodeName.SCORE)
    graph.add_edge(NodeName.SCORE, NodeName.VERIFY)
    graph.add_edge(NodeName.VERIFY, NodeName.SYNTHESIZE)
    graph.add_edge(NodeName.SYNTHESIZE, END)
    return graph


def compile_graph(
    deps: Deps,
    checkpointer: BaseCheckpointSaver | None = None,
    interrupt_before: list[str] | None = None,
):
    return build_state_graph(deps).compile(
        checkpointer=checkpointer or MemorySaver(),
        interrupt_before=interrupt_before or [],
    )


def _summarize_node_update(node_update: dict[str, Any]) -> dict[str, Any]:
    """Reduce a node's partial-state update to cheap counts for `detail`.

    The raw update can carry full lists (sources, claims, ...); a
    STAGE_COMPLETED event only needs to tell a client how many of each there
    are now, not ship the lists themselves over Redis/SSE.
    """
    detail: dict[str, Any] = {}
    for field_name in NODE_UPDATE_LIST_FIELDS:
        if field_name in node_update:
            detail[f"{field_name}_count"] = len(node_update[field_name])
    if "cost" in node_update:
        cost = node_update["cost"]
        detail["cost_usd"] = cost.usd if isinstance(cost, CostMeter) else cost["usd"]
    return detail


def _stage_completed_event(
    research_id: str,
    stage: str,
    status: ResearchStatus,
    node_update: dict[str, Any],
) -> ProgressEvent:
    return ProgressEvent(
        research_id=research_id,
        event_type=ProgressEventType.STAGE_COMPLETED,
        stage=stage,
        status=status,
        message=STAGE_COMPLETED_MESSAGE_TEMPLATE.format(stage=stage),
        detail=_summarize_node_update(node_update),
    )


def run_pipeline(
    state: ResearchState,
    deps: Deps,
    checkpointer: BaseCheckpointSaver | None = None,
    *,
    thread_id: str | None = None,
    callbacks: list[BaseCallbackHandler] | None = None,
    on_progress_event: ProgressEventSink | None = None,
) -> ResearchState:
    """Run the full graph and return the same state object, updated in place."""
    compiled_graph = compile_graph(deps, checkpointer=checkpointer)
    config: dict[str, Any] = {
        "configurable": {"thread_id": thread_id or state.research_id}
    }
    if callbacks:
        config["callbacks"] = callbacks

    # Seed from the input state's own field values (not a serialized dump) so
    # accumulation below matches exactly what `.invoke()` used to hand back:
    # each node returns only the fields it changed, and every ResearchState
    # field is a plain (last-value) channel, so later updates simply overwrite
    # earlier ones per key.
    accumulated_state: dict[str, Any] = {
        field_name: getattr(state, field_name) for field_name in ResearchState.model_fields
    }

    for stream_mode, payload in compiled_graph.stream(
        state,
        config,
        stream_mode=[GraphStreamMode.UPDATES, GraphStreamMode.CUSTOM],
        subgraphs=False,
    ):
        if stream_mode == GraphStreamMode.CUSTOM:
            if on_progress_event is not None:
                on_progress_event(payload)
            continue

        # "updates": {node_name: partial_state_update (or None if unchanged)}
        for node_name, node_update in payload.items():
            if not node_update:
                continue
            accumulated_state.update(node_update)
            if on_progress_event is not None:
                on_progress_event(
                    _stage_completed_event(
                        state.research_id,
                        node_name.value,
                        accumulated_state["status"],
                        node_update,
                    )
                )

    final_state = ResearchState.model_validate(accumulated_state)
    for field_name in ResearchState.model_fields:
        setattr(state, field_name, getattr(final_state, field_name))
    return state
