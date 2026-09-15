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

from functools import partial
from typing import Any

from langchain_core.callbacks import BaseCallbackHandler
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from src.models.schemas import ResearchState, WorkflowRoute
from src.workflows.nodes import (
    Deps,
    NodeName,
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


def run_pipeline(
    state: ResearchState,
    deps: Deps,
    checkpointer: BaseCheckpointSaver | None = None,
    *,
    thread_id: str | None = None,
    callbacks: list[BaseCallbackHandler] | None = None,
) -> ResearchState:
    """Run the full graph and return the same state object, updated in place."""
    compiled_graph = compile_graph(deps, checkpointer=checkpointer)
    config: dict[str, Any] = {
        "configurable": {"thread_id": thread_id or state.research_id}
    }
    if callbacks:
        config["callbacks"] = callbacks
    final_values = compiled_graph.invoke(state, config)
    final_state = ResearchState.model_validate(final_values)
    for field_name in ResearchState.model_fields:
        setattr(state, field_name, getattr(final_state, field_name))
    return state
