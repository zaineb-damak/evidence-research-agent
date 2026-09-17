"""run_pipeline's on_progress_event stream: stage-started/substep/stage-completed
events arrive, in order, for a full run — the highest-risk part of switching
`run_pipeline` from `compiled_graph.invoke()` to `compiled_graph.stream()`.
"""

from __future__ import annotations

from src.models.progress import ProgressEventType
from src.models.schemas import NodeName, ResearchDepth, ResearchState, ResearchStatus
from src.workflows.research import run_pipeline
from tests.conftest import make_deps


def test_run_pipeline_emits_expected_progress_event_sequence(
    fake_llm, fake_embedder, fake_connectors
):
    deps, _index, _graph = make_deps(fake_llm, fake_embedder, fake_connectors)
    state = ResearchState(
        original_question="What context length does Model X support?",
        depth=ResearchDepth.FAST,
    )
    events = []

    result = run_pipeline(state, deps, on_progress_event=events.append)

    assert result.status == ResearchStatus.COMPLETED

    # Every stage got a STAGE_STARTED followed later by a STAGE_COMPLETED, in
    # graph order.
    started_stages = [e.stage for e in events if e.event_type == ProgressEventType.STAGE_STARTED]
    completed_stages = [
        e.stage for e in events if e.event_type == ProgressEventType.STAGE_COMPLETED
    ]
    expected_order = [
        NodeName.PLAN.value,
        NodeName.SEARCH.value,
        NodeName.EXTRACT.value,
        NodeName.SCORE.value,
        NodeName.VERIFY.value,
        NodeName.SYNTHESIZE.value,
    ]
    assert started_stages == expected_order
    assert completed_stages == expected_order

    # search reports a substep per source found, with a running count.
    search_substeps = [
        e
        for e in events
        if e.event_type == ProgressEventType.SUBSTEP and e.stage == NodeName.SEARCH.value
    ]
    assert search_substeps
    assert search_substeps[0].detail["sources_found"] == 1

    # extract reports running claim/task counts per research task.
    extract_substeps = [
        e
        for e in events
        if e.event_type == ProgressEventType.SUBSTEP and e.stage == NodeName.EXTRACT.value
    ]
    assert extract_substeps
    assert extract_substeps[-1].detail["tasks_done"] == extract_substeps[-1].detail["tasks_total"]
    assert extract_substeps[-1].detail["claims_extracted"] >= 1

    # verify reports its three internal phases.
    verify_substeps = [
        e
        for e in events
        if e.event_type == ProgressEventType.SUBSTEP and e.stage == NodeName.VERIFY.value
    ]
    assert len(verify_substeps) == 3

    # A completed run only produces STAGE_STARTED/STAGE_COMPLETED/SUBSTEP
    # events — the terminal DONE/ERROR event is built separately, by the
    # caller, after run_pipeline returns (see build_terminal_event).
    assert all(
        e.event_type
        in (
            ProgressEventType.STAGE_STARTED,
            ProgressEventType.STAGE_COMPLETED,
            ProgressEventType.SUBSTEP,
        )
        for e in events
    )


def test_run_pipeline_without_on_progress_event_is_unaffected(
    fake_llm, fake_embedder, fake_connectors
):
    """Default (no on_progress_event) behaves exactly as before the .stream() switch."""
    deps, _index, _graph = make_deps(fake_llm, fake_embedder, fake_connectors)
    state = ResearchState(
        original_question="What context length does Model X support?",
        depth=ResearchDepth.FAST,
    )

    result = run_pipeline(state, deps)

    assert result.status == ResearchStatus.COMPLETED
    assert result.claims
    assert result.report
