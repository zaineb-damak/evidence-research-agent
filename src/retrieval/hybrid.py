"""Hybrid retrieval via Reciprocal Rank Fusion (RRF).

Fuses the keyword and semantic ranked lists without needing calibrated scores,
then applies the (identity, in v1) reranker. RRF score for a passage is
sum over lists of 1 / (k + rank).
"""

from __future__ import annotations

from src.retrieval.reranker import IdentityReranker, Reranker

RRF_K = 60


def rrf_fuse(
    ranked_lists: list[list[str]], k: int = RRF_K
) -> list[tuple[str, float]]:
    """ranked_lists: each is passage_ids in descending relevance."""
    scores: dict[str, float] = {}
    for ranked in ranked_lists:
        for rank, pid in enumerate(ranked):
            scores[pid] = scores.get(pid, 0.0) + 1.0 / (k + rank + 1)
    fused = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return fused


def hybrid_rank(
    query: str,
    keyword_ids: list[str],
    semantic_ids: list[str],
    passage_texts: dict[str, str],
    top_k: int,
    reranker: Reranker | None = None,
) -> list[str]:
    fused = rrf_fuse([keyword_ids, semantic_ids])
    reranker = reranker or IdentityReranker()
    candidates = [(pid, passage_texts.get(pid, "")) for pid, _ in fused]
    return reranker.rerank(query, candidates, top_k)
