"""Passage index — the retrieval backend for a research job.

Owns passage storage and both retrieval arms:
- keyword search over Postgres full-text search (tsvector / ts_rank), and
- semantic search over Qdrant vectors.

`PostgresQdrantPassageIndex` is the production implementation.
`InMemoryPassageIndex` is a test double using the pure-Python rankers, so the
pipeline runs in tests without a database. Both satisfy `PassageIndex`.

The index is the sole writer of the `passages` table; the job repository owns
every other table, so there is no double-write on save.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from langchain_core.embeddings import Embeddings
from sqlalchemy import bindparam, text

from src.db.base import session_scope
from src.models.db import PassageRow
from src.models.schemas import Passage
from src.retrieval.keyword import keyword_rank
from src.retrieval.semantic import semantic_rank_inmemory
from src.stores.vector import JOB_ID_PAYLOAD_KEY, QdrantVectorStore

FTS_LANGUAGE = "english"

_KEYWORD_SEARCH_SQL = text(
    """
    SELECT id
    FROM passages
    WHERE job_id = :job_id
      AND search_vector @@ plainto_tsquery(:language, :query)
    ORDER BY ts_rank(search_vector, plainto_tsquery(:language, :query)) DESC
    LIMIT :limit
    """
).bindparams(bindparam("language"), bindparam("query"), bindparam("limit"))


@runtime_checkable
class PassageIndex(Protocol):
    def add_passages(
        self, job_id: str, passages: list[Passage], vectors: dict[str, list[float]]
    ) -> None: ...

    def keyword_search(self, job_id: str, query: str, limit: int) -> list[str]: ...

    def semantic_search(
        self, job_id: str, query_vector: list[float], limit: int
    ) -> list[str]: ...


class PostgresQdrantPassageIndex:
    def __init__(self, vector_store: QdrantVectorStore):
        self._vector_store = vector_store

    def add_passages(
        self, job_id: str, passages: list[Passage], vectors: dict[str, list[float]]
    ) -> None:
        self._vector_store.ensure_collection()
        with session_scope() as session:
            for passage in passages:
                vector = vectors.get(passage.id)
                if vector is not None:
                    passage.qdrant_point_id = self._vector_store.upsert(
                        passage_id=passage.id,
                        vector=vector,
                        payload={
                            JOB_ID_PAYLOAD_KEY: job_id,
                            "source_id": passage.source_id,
                        },
                    )
                session.add(
                    PassageRow(
                        id=passage.id,
                        job_id=job_id,
                        document_id=passage.document_id,
                        source_id=passage.source_id,
                        text=passage.text,
                        ordinal=passage.ordinal,
                        qdrant_point_id=passage.qdrant_point_id,
                    )
                )

    def keyword_search(self, job_id: str, query: str, limit: int) -> list[str]:
        with session_scope() as session:
            rows = session.execute(
                _KEYWORD_SEARCH_SQL,
                {"job_id": job_id, "language": FTS_LANGUAGE, "query": query, "limit": limit},
            ).all()
        return [row[0] for row in rows]

    def semantic_search(
        self, job_id: str, query_vector: list[float], limit: int
    ) -> list[str]:
        hits = self._vector_store.search(query_vector, top_k=limit, job_id=job_id)
        return [hit.passage_id for hit in hits]


class InMemoryPassageIndex:
    """Test double: keeps passages/vectors in process, ranks with pure Python."""

    def __init__(self) -> None:
        self._passages_by_job: dict[str, list[Passage]] = {}
        self._vectors_by_job: dict[str, dict[str, list[float]]] = {}

    def add_passages(
        self, job_id: str, passages: list[Passage], vectors: dict[str, list[float]]
    ) -> None:
        self._passages_by_job.setdefault(job_id, []).extend(passages)
        self._vectors_by_job.setdefault(job_id, {}).update(vectors)

    def keyword_search(self, job_id: str, query: str, limit: int) -> list[str]:
        passages = self._passages_by_job.get(job_id, [])
        ranked = keyword_rank(
            query, [(passage.id, passage.text) for passage in passages], top_k=limit
        )
        return [passage_id for passage_id, _score in ranked]

    def semantic_search(
        self, job_id: str, query_vector: list[float], limit: int
    ) -> list[str]:
        vectors = self._vectors_by_job.get(job_id, {})
        ranked = semantic_rank_inmemory(
            query_vector, list(vectors.items()), top_k=limit
        )
        return [passage_id for passage_id, _score in ranked]


def build_embedded_vectors(
    embeddings: Embeddings, passages: list[Passage]
) -> dict[str, list[float]]:
    """Embed passage texts and map them by passage id."""
    if not passages:
        return {}
    vectors = embeddings.embed_documents([passage.text for passage in passages])
    return {passage.id: vector for passage, vector in zip(passages, vectors, strict=False)}
