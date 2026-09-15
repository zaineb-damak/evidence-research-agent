"""Reranker interface with an identity (no-op) implementation.

Reranking is intentionally skipped in v1 (no paid API budget). The interface is
here so a Cohere/Voyage cross-encoder can drop in later without touching the
hybrid pipeline. The identity reranker preserves fusion order.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class Reranker(Protocol):
    def rerank(self, query: str, passages: list[tuple[str, str]], top_k: int) -> list[str]: ...


class IdentityReranker:
    """Returns passage ids in their incoming (fused) order, truncated to top_k."""

    def rerank(self, query: str, passages: list[tuple[str, str]], top_k: int) -> list[str]:
        return [pid for pid, _text in passages[:top_k]]
