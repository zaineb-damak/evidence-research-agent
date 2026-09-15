"""Run the pipeline over a benchmark case and score it (§20).

Dependency-injected so the evaluation harness runs against fakes in tests and
against live providers in CI. Produces a CaseResult with retrieval, citation,
generation, contradiction, and system metrics.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from src.evaluation.dataset import BenchmarkCase, BenchmarkDataset
from src.evaluation.metrics.citation import citation_completeness, citation_correctness
from src.evaluation.metrics.generation import (
    claim_coverage,
    groundedness,
    topic_completeness,
)
from src.evaluation.metrics.retrieval import ndcg_at_k, recall_at_k, reciprocal_rank
from src.models.schemas import ResearchState
from src.workflows.research import Deps, run_pipeline

RECALL_AT_5 = 5
RECALL_AT_10 = 10
NDCG_K = 10
PERFECT_SCORE = 1.0


class CaseResult(BaseModel):
    case_id: str
    recall_at_5: float
    recall_at_10: float
    mean_reciprocal_rank: float
    ndcg_at_10: float
    citation_correctness: float
    citation_completeness: float
    topic_completeness: float
    groundedness: float
    claim_coverage: float
    contradiction_recall: float
    cost_usd: float
    latency_ms: int


class DatasetResult(BaseModel):
    dataset_name: str
    case_results: list[CaseResult] = Field(default_factory=list)

    def mean(self, metric_name: str) -> float:
        if not self.case_results:
            return 0.0
        values = [getattr(result, metric_name) for result in self.case_results]
        return sum(values) / len(values)


def _contradiction_recall(case: BenchmarkCase, state: ResearchState) -> float:
    expected_count = len(case.known_contradictions)
    if expected_count == 0:
        return PERFECT_SCORE
    detected_count = len(state.contradictions)
    return min(detected_count / expected_count, PERFECT_SCORE)


def evaluate_case(case: BenchmarkCase, state: ResearchState) -> CaseResult:
    retrieved_source_urls = [source.url for source in state.sources]
    relevant_source_urls = set(case.expected_source_urls)

    return CaseResult(
        case_id=case.case_id,
        recall_at_5=recall_at_k(retrieved_source_urls, relevant_source_urls, RECALL_AT_5),
        recall_at_10=recall_at_k(retrieved_source_urls, relevant_source_urls, RECALL_AT_10),
        mean_reciprocal_rank=reciprocal_rank(retrieved_source_urls, relevant_source_urls),
        ndcg_at_10=ndcg_at_k(retrieved_source_urls, relevant_source_urls, NDCG_K),
        citation_correctness=citation_correctness(state.claims, state.evidence),
        citation_completeness=citation_completeness(state.claims),
        topic_completeness=topic_completeness(state.report, case.required_topics),
        groundedness=groundedness(state.claims),
        claim_coverage=claim_coverage(state.claims, case.expected_claims),
        contradiction_recall=_contradiction_recall(case, state),
        cost_usd=state.cost.usd,
        latency_ms=state.cost.latency_ms,
    )


def run_case(case: BenchmarkCase, deps: Deps) -> CaseResult:
    state = ResearchState(
        original_question=case.question,
        depth=case.depth,
        source_types=case.source_types,
    )
    run_pipeline(state, deps)
    return evaluate_case(case, state)


def run_dataset(dataset: BenchmarkDataset, deps: Deps) -> DatasetResult:
    return DatasetResult(
        dataset_name=dataset.name,
        case_results=[run_case(case, deps) for case in dataset.cases],
    )
