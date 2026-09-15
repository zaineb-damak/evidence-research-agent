"""Semantic arm: embed the query, cosine search.

Uses Qdrant when a VectorStore is provided; otherwise scores against in-memory
passage embeddings (unit tests / no-DB runs).
"""

from __future__ import annotations

import math


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def semantic_rank_inmemory(
    query_vec: list[float],
    passage_vecs: list[tuple[str, list[float]]],
    top_k: int,
) -> list[tuple[str, float]]:
    scored = [(pid, cosine(query_vec, vec)) for pid, vec in passage_vecs]
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:top_k]
