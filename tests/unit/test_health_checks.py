"""Readiness probe behaviour: aggregation, failure isolation, and timeouts.

Probes are injected, so no Postgres/Redis/Neo4j/Qdrant is needed — the contract
under test is how `check_readiness` reports them, not the drivers themselves.
"""

from __future__ import annotations

import time

from src.config import Settings
from src.health.checks import (
    DependencyStatus,
    check_readiness,
)

FAST_TIMEOUT_SECONDS = 0.25
PROBE_FAILURE_MESSAGE = "connection refused"
SLEEP_PAST_TIMEOUT_SECONDS = FAST_TIMEOUT_SECONDS * 4

HEALTHY_DEPENDENCY = "healthy-store"
BROKEN_DEPENDENCY = "broken-store"
SLOW_DEPENDENCY = "slow-store"


def _settings() -> Settings:
    return Settings(readiness_timeout_seconds=FAST_TIMEOUT_SECONDS)


def _healthy_probe(_settings: Settings) -> None:
    return None


def _failing_probe(_settings: Settings) -> None:
    raise ConnectionError(PROBE_FAILURE_MESSAGE)


def _slow_probe(_settings: Settings) -> None:
    time.sleep(SLEEP_PAST_TIMEOUT_SECONDS)


def _by_name(report, name):
    return next(item for item in report.dependencies if item.name == name)


def test_all_dependencies_up_reports_ready():
    report = check_readiness(_settings(), probes={HEALTHY_DEPENDENCY: _healthy_probe})

    assert report.ready is True
    assert _by_name(report, HEALTHY_DEPENDENCY).status is DependencyStatus.UP
    assert report.as_dict()["status"] == DependencyStatus.UP.value


def test_one_failing_dependency_makes_the_report_not_ready():
    report = check_readiness(
        _settings(),
        probes={HEALTHY_DEPENDENCY: _healthy_probe, BROKEN_DEPENDENCY: _failing_probe},
    )

    assert report.ready is False
    # The healthy dependency is still reported as up: readiness says *which*
    # dependency is down, which is the whole point of the payload.
    assert _by_name(report, HEALTHY_DEPENDENCY).status is DependencyStatus.UP
    broken = _by_name(report, BROKEN_DEPENDENCY)
    assert broken.status is DependencyStatus.DOWN
    assert PROBE_FAILURE_MESSAGE in broken.detail


def test_a_hanging_probe_is_cut_off_at_the_timeout():
    started_at = time.monotonic()
    report = check_readiness(_settings(), probes={SLOW_DEPENDENCY: _slow_probe})
    elapsed_seconds = time.monotonic() - started_at

    assert report.ready is False
    assert _by_name(report, SLOW_DEPENDENCY).status is DependencyStatus.DOWN
    # The probe would have slept far past the deadline; the check must not.
    assert elapsed_seconds < SLEEP_PAST_TIMEOUT_SECONDS


def test_probes_share_one_deadline_rather_than_one_each():
    """Two hanging probes must not cost two timeouts — they run concurrently."""
    started_at = time.monotonic()
    check_readiness(
        _settings(),
        probes={SLOW_DEPENDENCY: _slow_probe, BROKEN_DEPENDENCY: _slow_probe},
    )
    elapsed_seconds = time.monotonic() - started_at

    assert elapsed_seconds < FAST_TIMEOUT_SECONDS * 2


def test_no_probes_is_trivially_ready():
    report = check_readiness(_settings(), probes={})

    assert report.ready is True
    assert report.dependencies == ()
