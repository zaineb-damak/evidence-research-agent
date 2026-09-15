"""Retrieval quality metrics: Recall@k, MRR, nDCG (binary relevance).

All operate on a ranked list of retrieved ids and a set of relevant ids. This is
where the impact of skipping the reranker in v1 is measured.
"""

from __future__ import annotations

import math

FIRST_RANK = 1
LOG_BASE_OFFSET = 1  # nDCG discounts by log2(rank + 1)
PERFECT_SCORE = 1.0
ZERO_SCORE = 0.0


def recall_at_k(retrieved_ids: list[str], relevant_ids: set[str], k: int) -> float:
    if not relevant_ids:
        return PERFECT_SCORE
    top_k = set(retrieved_ids[:k])
    found = len(top_k & relevant_ids)
    return found / len(relevant_ids)


def reciprocal_rank(retrieved_ids: list[str], relevant_ids: set[str]) -> float:
    for rank, retrieved_id in enumerate(retrieved_ids, start=FIRST_RANK):
        if retrieved_id in relevant_ids:
            return PERFECT_SCORE / rank
    return ZERO_SCORE


def ndcg_at_k(retrieved_ids: list[str], relevant_ids: set[str], k: int) -> float:
    if not relevant_ids:
        return PERFECT_SCORE

    discounted_cumulative_gain = ZERO_SCORE
    for rank, retrieved_id in enumerate(retrieved_ids[:k], start=FIRST_RANK):
        if retrieved_id in relevant_ids:
            discounted_cumulative_gain += PERFECT_SCORE / math.log2(rank + LOG_BASE_OFFSET)

    ideal_relevant_count = min(len(relevant_ids), k)
    ideal_discounted_cumulative_gain = sum(
        PERFECT_SCORE / math.log2(rank + LOG_BASE_OFFSET)
        for rank in range(FIRST_RANK, ideal_relevant_count + FIRST_RANK)
    )
    if ideal_discounted_cumulative_gain == ZERO_SCORE:
        return ZERO_SCORE
    return discounted_cumulative_gain / ideal_discounted_cumulative_gain
