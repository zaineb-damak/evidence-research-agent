"""FastAPI dependency providers for the persistence-backed API.

Production wires the Postgres job repository, the Neo4j graph store, and a Celery
enqueuer. Tests override these with in-memory doubles / a synchronous runner.
"""

from __future__ import annotations

from collections.abc import Callable
from functools import lru_cache

from src.config import get_settings
from src.db.repository import JobRepository, PostgresJobRepository
from src.db.users import PostgresUserRepository, UserRepository
from src.stores.graph import GraphStore, Neo4jGraphStore

JobEnqueuer = Callable[[str], None]


def get_repository() -> JobRepository:
    return PostgresJobRepository()


def get_user_repository() -> UserRepository:
    return PostgresUserRepository()


@lru_cache
def _cached_graph_store() -> Neo4jGraphStore:
    settings = get_settings()
    return Neo4jGraphStore(
        uri=settings.neo4j_uri,
        user=settings.neo4j_user,
        password=settings.neo4j_password,
    )


def get_graph_store() -> GraphStore:
    return _cached_graph_store()


def get_job_enqueuer() -> JobEnqueuer:
    # Imported here so the API module does not require Celery/broker at import
    # time (keeps the app importable in environments without a broker).
    from apps.worker.celery_app import run_research_task

    def enqueue(research_id: str) -> None:
        run_research_task.delay(research_id)

    return enqueue
