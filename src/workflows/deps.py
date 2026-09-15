"""Assemble live pipeline dependencies from settings.

Wires the real backends: LangChain LLM + embedder, the source connectors, the
Postgres+Qdrant passage index, and the Neo4j graph store.
"""

from __future__ import annotations

from src.config import Settings, get_settings
from src.embeddings.factory import build_embedder
from src.llm.factory import build_llm
from src.models.schemas import SourceType
from src.retrieval.index import PostgresQdrantPassageIndex
from src.sources.registry import build_connectors
from src.stores.graph import Neo4jGraphStore
from src.stores.vector import QdrantVectorStore
from src.workflows.nodes import Deps


def build_deps(
    source_types: list[SourceType], settings: Settings | None = None
) -> Deps:
    settings = settings or get_settings()

    vector_store = QdrantVectorStore(
        url=settings.qdrant_url,
        collection=settings.qdrant_collection,
        dim=settings.embed_dim,
    )
    graph_store = Neo4jGraphStore(
        uri=settings.neo4j_uri,
        user=settings.neo4j_user,
        password=settings.neo4j_password,
    )
    graph_store.ensure_constraints()

    return Deps(
        llm=build_llm(settings),
        embeddings=build_embedder(settings),
        connectors=build_connectors(source_types, settings),
        passage_index=PostgresQdrantPassageIndex(vector_store=vector_store),
        graph_store=graph_store,
    )
