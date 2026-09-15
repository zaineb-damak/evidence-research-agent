"""Hybrid retrieval over a PassageIndex.

Runs the keyword and semantic arms against the index for one job, then fuses the
two ranked id lists with Reciprocal Rank Fusion. Kept separate from the workflow
so orchestration stays focused on control flow.
"""

from __future__ import annotations

from langchain_core.embeddings import Embeddings

from src.retrieval.hybrid import rrf_fuse
from src.retrieval.index import PassageIndex
from src.retrieval.reranker import IdentityReranker, Reranker

# How many candidates each retrieval arm contributes before RRF fusion.
RETRIEVAL_ARM_CANDIDATES = 20


def retrieve_top_passages(
    job_id: str,
    query: str,
    index: PassageIndex,
    embeddings: Embeddings,
    top_k: int,
    reranker: Reranker | None = None,
) -> list[str]:
    """Return the ids of the top passages for a query via hybrid RRF."""
    keyword_ids = index.keyword_search(job_id, query, RETRIEVAL_ARM_CANDIDATES)

    query_vector = embeddings.embed_query(query)
    semantic_ids = index.semantic_search(job_id, query_vector, RETRIEVAL_ARM_CANDIDATES)

    fused = rrf_fuse([keyword_ids, semantic_ids])
    fused_ids = [passage_id for passage_id, _score in fused]

    reranker = reranker or IdentityReranker()
    # The reranker takes (id, text) pairs; text is not needed for the identity
    # reranker, so ids are paired with empty text here.
    return reranker.rerank(query, [(passage_id, "") for passage_id in fused_ids], top_k)
