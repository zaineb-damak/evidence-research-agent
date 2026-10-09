"""Dependency probes behind the readiness endpoint.

Kubernetes distinguishes *liveness* ("is this process wedged — restart it") from
*readiness* ("can this process serve traffic right now — route to it"). Liveness
must never depend on a backing service: a Postgres blip would otherwise restart
every API pod and turn a recoverable outage into a crash loop. So only readiness
probes dependencies, and only the ones a request actually needs.

Every probe is bounded twice: the client gets a real socket timeout so it
returns on its own, and the future gets a wall-clock timeout as a backstop.
Probes run concurrently, so a readiness check costs the slowest dependency
rather than the sum of all four.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from dataclasses import dataclass
from enum import StrEnum
from functools import lru_cache

import redis
from neo4j import GraphDatabase
from qdrant_client import QdrantClient
from sqlalchemy import text

from src.clock import MILLISECONDS_PER_SECOND
from src.config import Settings, get_settings
from src.db.base import get_engine

POSTGRES_DEPENDENCY = "postgres"
REDIS_DEPENDENCY = "redis"
NEO4J_DEPENDENCY = "neo4j"
QDRANT_DEPENDENCY = "qdrant"

LIVENESS_QUERY = text("SELECT 1")

# One worker per dependency so the four probes overlap instead of queueing.
PROBE_THREAD_NAME_PREFIX = "readiness-probe"

# Reported instead of an empty string when a probe fails without a message.
UNKNOWN_FAILURE_DETAIL = "probe failed without a message"
TIMEOUT_DETAIL_TEMPLATE = "probe exceeded {timeout_seconds}s"


class DependencyStatus(StrEnum):
    UP = "up"
    DOWN = "down"


@dataclass(frozen=True)
class DependencyHealth:
    name: str
    status: DependencyStatus
    latency_ms: int
    detail: str | None = None

    def as_dict(self) -> dict:
        return {
            "name": self.name,
            "status": self.status.value,
            "latency_ms": self.latency_ms,
            "detail": self.detail,
        }


@dataclass(frozen=True)
class ReadinessReport:
    dependencies: tuple[DependencyHealth, ...]

    @property
    def ready(self) -> bool:
        return all(
            dependency.status is DependencyStatus.UP for dependency in self.dependencies
        )

    def as_dict(self) -> dict:
        return {
            "status": (DependencyStatus.UP if self.ready else DependencyStatus.DOWN).value,
            "dependencies": [dependency.as_dict() for dependency in self.dependencies],
        }


def _probe_postgres(settings: Settings) -> None:
    # The pooled engine already has pool_pre_ping, so this validates a live
    # connection without opening a new one on every probe.
    with get_engine().connect() as connection:
        connection.execute(LIVENESS_QUERY)


@lru_cache
def _readiness_redis_client(redis_url: str, timeout_seconds: float) -> redis.Redis:
    return redis.Redis.from_url(
        redis_url,
        socket_timeout=timeout_seconds,
        socket_connect_timeout=timeout_seconds,
    )


def _probe_redis(settings: Settings) -> None:
    _readiness_redis_client(settings.redis_url, settings.readiness_timeout_seconds).ping()


@lru_cache
def _readiness_neo4j_driver(uri: str, user: str, password: str, timeout_seconds: float):
    return GraphDatabase.driver(
        uri,
        auth=(user, password),
        connection_timeout=timeout_seconds,
        connection_acquisition_timeout=timeout_seconds,
    )


def _probe_neo4j(settings: Settings) -> None:
    _readiness_neo4j_driver(
        settings.neo4j_uri,
        settings.neo4j_user,
        settings.neo4j_password,
        settings.readiness_timeout_seconds,
    ).verify_connectivity()


@lru_cache
def _readiness_qdrant_client(url: str, timeout_seconds: float) -> QdrantClient:
    # Qdrant's client takes whole seconds.
    return QdrantClient(url=url, timeout=max(1, int(timeout_seconds)))


def _probe_qdrant(settings: Settings) -> None:
    _readiness_qdrant_client(
        settings.qdrant_url, settings.readiness_timeout_seconds
    ).get_collections()


DependencyProbe = Callable[[Settings], None]

# Every dependency an API request can touch. The worker shares this set.
DEPENDENCY_PROBES: dict[str, DependencyProbe] = {
    POSTGRES_DEPENDENCY: _probe_postgres,
    REDIS_DEPENDENCY: _probe_redis,
    NEO4J_DEPENDENCY: _probe_neo4j,
    QDRANT_DEPENDENCY: _probe_qdrant,
}


@lru_cache
def _probe_executor(max_workers: int) -> ThreadPoolExecutor:
    return ThreadPoolExecutor(
        max_workers=max_workers, thread_name_prefix=PROBE_THREAD_NAME_PREFIX
    )


def _resolve(
    name: str, future: Future, submitted_at: float, deadline: float, timeout_seconds: float
) -> DependencyHealth:
    # A single deadline shared by all probes: they run concurrently, so the
    # whole readiness check is bounded by one timeout rather than by one per
    # dependency.
    try:
        future.result(timeout=max(0.0, deadline - time.monotonic()))
    except FutureTimeoutError:
        detail = TIMEOUT_DETAIL_TEMPLATE.format(timeout_seconds=timeout_seconds)
        status = DependencyStatus.DOWN
    except Exception as error:  # noqa: BLE001 — any driver error means "not ready"
        detail = str(error) or UNKNOWN_FAILURE_DETAIL
        status = DependencyStatus.DOWN
    else:
        detail = None
        status = DependencyStatus.UP

    elapsed_ms = int((time.monotonic() - submitted_at) * MILLISECONDS_PER_SECOND)
    return DependencyHealth(name=name, status=status, latency_ms=elapsed_ms, detail=detail)


def check_readiness(
    settings: Settings | None = None, probes: dict[str, DependencyProbe] | None = None
) -> ReadinessReport:
    settings = settings or get_settings()
    probes = probes if probes is not None else DEPENDENCY_PROBES
    if not probes:
        return ReadinessReport(dependencies=())

    timeout_seconds = settings.readiness_timeout_seconds
    executor = _probe_executor(len(probes))
    # One worker per probe, so each starts immediately and its submit time is
    # also its start time.
    submitted = {
        name: (executor.submit(probe, settings), time.monotonic())
        for name, probe in probes.items()
    }
    deadline = time.monotonic() + timeout_seconds
    return ReadinessReport(
        dependencies=tuple(
            _resolve(name, future, submitted_at, deadline, timeout_seconds)
            for name, (future, submitted_at) in submitted.items()
        )
    )
