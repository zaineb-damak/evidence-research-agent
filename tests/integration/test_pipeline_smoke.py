"""End-to-end smoke test of the research pipeline with all deps faked."""

from __future__ import annotations

from src.models.schemas import ResearchDepth, ResearchState, ResearchStatus
from src.workflows.research import run_pipeline
from tests.conftest import make_deps


def test_pipeline_produces_cited_report(fake_llm, fake_embedder, fake_connectors):
    state = ResearchState(
        original_question="What context length does Model X support?",
        depth=ResearchDepth.FAST,
    )
    deps, _index, _graph = make_deps(fake_llm, fake_embedder, fake_connectors)

    result = run_pipeline(state, deps)

    assert result.status == ResearchStatus.COMPLETED
    assert result.sources, "expected at least one source"
    assert result.claims, "expected at least one extracted claim"

    claim = result.claims[0]
    # Claim is backed by real evidence (never generated text).
    assert claim.evidence_ids
    assert 0.0 <= claim.confidence <= 1.0

    # Report has the required structure and a per-claim citation marker.
    report = result.report
    assert "# Research Report" in report
    assert "## Sources" in report
    assert "[1]" in report  # citation attached to a claim
    assert "docs.example.com" in report


def test_confidence_is_measurable(fake_llm, fake_embedder, fake_connectors):
    state = ResearchState(original_question="Q?", depth=ResearchDepth.FAST)
    deps, _index, _graph = make_deps(fake_llm, fake_embedder, fake_connectors)
    result = run_pipeline(state, deps)

    b = result.claims[0].confidence_breakdown
    # Every factor populated; total is their product.
    assert b.total <= min(b.source_quality, b.evidence_strength) + 1e-9
