"""Keyword arm.

In production this uses Postgres full-text search (`ts_rank`) over the
`passages.tsvector` column. For in-memory runs and unit tests it falls back to a
token-overlap scorer so the hybrid pipeline is exercisable without a database.
"""

from __future__ import annotations

from collections import Counter

from src.text.tokenize import tokens


def keyword_rank(
    query: str, passages: list[tuple[str, str]], top_k: int
) -> list[tuple[str, float]]:
    """passages: list of (passage_id, text). Returns [(passage_id, score)] desc."""
    q_terms = Counter(tokens(query))
    if not q_terms:
        return []
    scored: list[tuple[str, float]] = []
    for pid, text in passages:
        terms = Counter(tokens(text))
        overlap = sum(min(terms[t], q_terms[t]) for t in q_terms)
        if overlap:
            # length-normalized overlap
            scored.append((pid, overlap / (1 + len(terms) ** 0.5)))
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:top_k]
