"""End-to-end evaluation: run the example dataset through the pipeline with
fakes and confirm the regression gate passes."""

from __future__ import annotations

from pathlib import Path

from src.evaluation.dataset import load_dataset
from src.evaluation.gate import evaluate_gate, gate_passed
from src.evaluation.runner import run_dataset
from tests.conftest import make_deps

DATASET_PATH = Path(__file__).parents[2] / "evals" / "datasets" / "example.json"


def test_example_dataset_passes_gate(fake_llm, fake_embedder, fake_connectors):
    dataset = load_dataset(DATASET_PATH)
    deps, _index, _graph = make_deps(fake_llm, fake_embedder, fake_connectors)

    result = run_dataset(dataset, deps)

    assert result.case_results, "expected at least one case result"
    case = result.case_results[0]
    # The fake docs source is the expected source, so retrieval should be perfect.
    assert case.recall_at_5 == 1.0
    assert case.citation_correctness == 1.0
    assert case.claim_coverage == 1.0

    failures = evaluate_gate(result)
    assert gate_passed(result), f"gate failed: {failures}"
