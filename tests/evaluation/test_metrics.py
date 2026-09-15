"""Unit tests for evaluation metrics."""

from __future__ import annotations

import pytest

from src.evaluation.metrics.citation import citation_completeness, citation_correctness
from src.evaluation.metrics.generation import groundedness, topic_completeness
from src.evaluation.metrics.retrieval import ndcg_at_k, recall_at_k, reciprocal_rank
from src.models.schemas import Claim, ClaimStatus, Evidence


def test_recall_at_k_counts_only_top_k():
    retrieved = ["a", "b", "c", "d"]
    relevant = {"c", "d"}
    assert recall_at_k(retrieved, relevant, k=2) == 0.0
    assert recall_at_k(retrieved, relevant, k=4) == 1.0


def test_reciprocal_rank_uses_first_hit():
    assert reciprocal_rank(["x", "y", "hit"], {"hit"}) == pytest.approx(1 / 3)
    assert reciprocal_rank(["hit"], {"hit"}) == 1.0
    assert reciprocal_rank(["miss"], {"hit"}) == 0.0


def test_ndcg_is_one_for_ideal_ranking():
    retrieved = ["a", "b", "c"]
    relevant = {"a", "b"}
    assert ndcg_at_k(retrieved, relevant, k=3) == pytest.approx(1.0)


def test_ndcg_penalizes_late_relevant_items():
    ideal = ndcg_at_k(["a", "b", "c"], {"a"}, k=3)
    late = ndcg_at_k(["c", "b", "a"], {"a"}, k=3)
    assert late < ideal


def test_citation_correctness_flags_unresolvable_citations():
    claim = Claim(text="cited but broken")
    claim.evidence_ids.append("missing-evidence-id")
    # Citation points at evidence that does not exist -> not supported.
    assert citation_correctness([claim], evidence=[]) == 0.0

    evidence = Evidence(claim_id=claim.id, passage_id="p", source_id="s", snippet="x")
    claim.evidence_ids = [evidence.id]
    assert citation_correctness([claim], [evidence]) == 1.0


def test_citation_completeness_ignores_unsupported_claims():
    supported = Claim(text="has citation", status=ClaimStatus.VERIFIED)
    supported.evidence_ids.append("e1")
    unsupported = Claim(text="no citation needed", status=ClaimStatus.UNSUPPORTED)
    assert citation_completeness([supported, unsupported]) == 1.0


def test_topic_completeness_and_groundedness():
    report = "The model supports a long context window."
    assert topic_completeness(report, ["context"]) == 1.0
    assert topic_completeness(report, ["multilingual"]) == 0.0

    grounded_claim = Claim(text="grounded")
    grounded_claim.evidence_ids.append("e1")
    floating_claim = Claim(text="floating")
    assert groundedness([grounded_claim, floating_claim]) == 0.5
