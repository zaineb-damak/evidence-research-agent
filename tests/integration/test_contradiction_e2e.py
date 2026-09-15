"""End-to-end: two sources give conflicting context lengths for the same model.

The pipeline must surface this as a CONTRADICTS relationship and a Conflicting
Evidence section — not silently pick one. Fakes are scripted so the run is
deterministic; a constant embedder forces the two claims to resolve as the
same subject so reconciliation fires.
"""

from __future__ import annotations

import re

from src.models.schemas import ResearchDepth, ResearchState, SourceType
from src.sources.base import RawResult
from src.workflows.research import run_pipeline
from tests.conftest import ConstantEmbeddings, make_deps, structured_llm


class TwoSourceConnector:
    source_type = SourceType.WEB

    def search(self, query: str, limit: int) -> list[RawResult]:
        return [
            RawResult(
                url="https://docs.example.com/x",
                title="Official Docs",
                content="Model X supports 128K context.",
                source_type=SourceType.DOCUMENTATION,
                domain="docs.example.com",
            ),
            RawResult(
                url="https://oldblog.example.com/x",
                title="Old Blog",
                content="Model X supports 32K context.",
                source_type=SourceType.WEB,
                domain="oldblog.example.com",
            ),
        ]


def _conflict_claims_from(prompt_text: str) -> list[dict]:
    claims = []
    for passage_id, value in re.findall(
        r"passage_id=(\S+).*?(128K|32K)", prompt_text, re.DOTALL
    ):
        claims.append(
            {
                "claim": f"Model X supports {value} context.",
                "passage_id": passage_id,
                "evidence_snippet": f"Model X supports {value} context.",
                "entities": [{"name": "Model X", "type": "model"}],
            }
        )
    return claims


def conflict_response(prompt_text: str) -> dict:
    if "research planner" in prompt_text:
        return {"sub_questions": ["What context length does Model X support?"]}
    if "extract factual claims" in prompt_text:
        return {"claims": _conflict_claims_from(prompt_text)}
    if "reconcile two candidate claims" in prompt_text:
        return {"relation": "contradiction"}
    if "evidence snippet supports the claim" in prompt_text:
        return {"entailment": "entailed"}
    if "executive summary" in prompt_text:
        return {"executive_summary": "Reports on Model X's context length conflict."}
    return {}


# A constant embedding forces the two claims to resolve as the same subject.
_CONSTANT_VECTOR = [1.0, 0.0, 0.0]


def test_conflicting_context_lengths_are_reported():
    state = ResearchState(
        original_question="What context length does Model X support?",
        depth=ResearchDepth.FAST,
    )
    deps, _index, graph_store = make_deps(
        structured_llm(conflict_response),
        ConstantEmbeddings(_CONSTANT_VECTOR),
        {SourceType.WEB: TwoSourceConnector()},
    )

    result = run_pipeline(state, deps)

    assert len(result.contradictions) == 1
    contra = result.contradictions[0]
    assert contra.resolved_winner_id is not None  # winner chosen, not silent

    assert "## Conflicting Evidence" in result.report
    assert "128K" in result.report and "32K" in result.report
    assert "No contradictions" not in result.report

    # The contradiction was persisted to the graph store as a CONTRADICTS edge.
    graph = graph_store.subgraph(result.research_id)
    assert any(edge["rel"] == "CONTRADICTS" for edge in graph["edges"])
