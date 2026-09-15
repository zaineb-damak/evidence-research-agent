"""LangGraph checkpoint/resume: an interrupted run resumes from the last
completed node without re-running earlier nodes (§18)."""

from __future__ import annotations

from langgraph.checkpoint.memory import MemorySaver

from src.models.schemas import ResearchDepth, ResearchState, SourceType
from src.workflows.research import NodeName, compile_graph
from tests.conftest import make_deps


class CountingConnectorWrapper:
    """Wraps a connector and counts how many times search() is called."""

    def __init__(self, inner):
        self._inner = inner
        self.source_type = inner.source_type
        self.search_calls = 0

    def search(self, query: str, limit: int):
        self.search_calls += 1
        return self._inner.search(query, limit)


def test_interrupted_run_resumes_without_re_searching(
    fake_llm, fake_embedder, fake_connectors
):
    counting = CountingConnectorWrapper(fake_connectors[SourceType.WEB])
    deps, _index, _graph = make_deps(
        fake_llm, fake_embedder, {SourceType.WEB: counting}
    )

    # Compile with a checkpointer and an interrupt right before synthesis.
    graph = compile_graph(
        deps,
        checkpointer=MemorySaver(),
        interrupt_before=[NodeName.SYNTHESIZE],
    )
    config = {"configurable": {"thread_id": "resume-test"}}
    state = ResearchState(
        original_question="What context length does Model X support?",
        depth=ResearchDepth.FAST,
    )

    # First invocation stops before synthesis: claims exist but no report yet.
    interrupted = graph.invoke(state, config)
    assert interrupted["claims"], "expected claims before the interrupt"
    assert interrupted["report"] == ""
    searches_before_resume = counting.search_calls
    assert searches_before_resume >= 1

    # Resuming (input=None) continues from the checkpoint and finishes without
    # re-running the search node.
    final = graph.invoke(None, config)
    assert final["report"], "resume should produce the report"
    assert counting.search_calls == searches_before_resume  # search not repeated
