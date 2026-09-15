"""Unit tests for RRF fusion, keyword ranking, and the confidence formula."""

from __future__ import annotations

from src.evidence.confidence import compute_confidence
from src.retrieval.hybrid import rrf_fuse
from src.retrieval.keyword import keyword_rank


def test_rrf_rewards_agreement_across_lists():
    # "b" ranks high in BOTH lists; "c"/"d" appear in only one. Fusion favors "b".
    fused = rrf_fuse([["c", "b", "a"], ["d", "b", "a"]])
    order = [pid for pid, _ in fused]
    assert order[0] == "b"
    assert order.index("a") < order.index("c")  # a (in both) beats c (in one)
    assert set(order) == {"a", "b", "c", "d"}


def test_keyword_rank_matches_overlap():
    passages = [
        ("p1", "context length tokens model"),
        ("p2", "unrelated cooking recipe"),
    ]
    ranked = keyword_rank("context length", passages, top_k=2)
    assert ranked[0][0] == "p1"


def test_confidence_is_product_of_factors():
    b = compute_confidence(
        source_quality=0.8,
        evidence_strength=0.5,
        corroborating_sources=3,  # → agreement 1.0
        extraction_confidence=0.5,
    )
    assert abs(b.source_agreement - 1.0) < 1e-9
    assert abs(b.total - (0.8 * 0.5 * 1.0 * 0.5)) < 1e-9


def test_confidence_clamps_and_penalizes_low_corroboration():
    b = compute_confidence(1.5, 1.0, 1, 1.0)  # sq clamps to 1.0, agreement 1/3
    assert b.source_quality == 1.0
    assert abs(b.source_agreement - (1 / 3)) < 1e-3  # rounded to 4 decimals
