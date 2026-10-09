"""Operational endpoints: liveness, readiness, metrics, and request correlation.

These are what Kubernetes and Prometheus consume, so the contract under test is
the one they rely on: probes answer without a token, readiness turns 503 when a
dependency is down, and metrics are labelled with the route *template*.
"""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from apps.api import dependencies, main  # noqa: E402
from apps.api.middleware import REQUEST_ID_HEADER  # noqa: E402
from apps.api.routes_health import (  # noqa: E402
    LIVENESS_PATH,
    METRICS_PATH,
    READINESS_PATH,
    SERVICE_UNAVAILABLE_STATUS,
)
from src.config import Settings, get_settings  # noqa: E402
from src.health.checks import (  # noqa: E402
    DependencyHealth,
    DependencyStatus,
    ReadinessReport,
)

OK_STATUS = 200
NOT_FOUND_STATUS = 404
UNAUTHORIZED_STATUS = 401

FAILING_DEPENDENCY = "postgres"
PROBE_FAILURE_DETAIL = "connection refused"
PROBE_LATENCY_MS = 3

CALLER_REQUEST_ID = "caller-supplied-request-id"
UNKNOWN_PATH = "/api/research/does-not-exist-route/nope"

HEALTHY_REPORT = ReadinessReport(
    dependencies=(
        DependencyHealth(
            name=FAILING_DEPENDENCY,
            status=DependencyStatus.UP,
            latency_ms=PROBE_LATENCY_MS,
        ),
    )
)
UNHEALTHY_REPORT = ReadinessReport(
    dependencies=(
        DependencyHealth(
            name=FAILING_DEPENDENCY,
            status=DependencyStatus.DOWN,
            latency_ms=PROBE_LATENCY_MS,
            detail=PROBE_FAILURE_DETAIL,
        ),
    )
)


@pytest.fixture
def client():
    main.app.dependency_overrides[get_settings] = Settings
    yield TestClient(main.app)
    main.app.dependency_overrides.clear()


def _override_readiness(report: ReadinessReport) -> None:
    main.app.dependency_overrides[dependencies.get_readiness_checker] = (
        lambda: lambda _settings: report
    )


def test_liveness_needs_no_token(client):
    response = client.get(LIVENESS_PATH)

    assert response.status_code == OK_STATUS


def test_readiness_is_ok_when_dependencies_are_up(client):
    _override_readiness(HEALTHY_REPORT)

    response = client.get(READINESS_PATH)

    assert response.status_code == OK_STATUS
    assert response.json()["status"] == DependencyStatus.UP.value


def test_readiness_is_503_and_names_the_failing_dependency(client):
    _override_readiness(UNHEALTHY_REPORT)

    response = client.get(READINESS_PATH)

    assert response.status_code == SERVICE_UNAVAILABLE_STATUS
    body = response.json()
    assert body["status"] == DependencyStatus.DOWN.value
    failing = body["dependencies"][0]
    assert failing["name"] == FAILING_DEPENDENCY
    assert failing["detail"] == PROBE_FAILURE_DETAIL


def test_metrics_exposes_request_counters_labelled_by_route_template(client):
    client.get(LIVENESS_PATH)

    response = client.get(METRICS_PATH)

    assert response.status_code == OK_STATUS
    body = response.text
    assert "http_requests_total" in body
    # The template, not a concrete path — otherwise every research id would mint
    # its own time series.
    assert f'route="{LIVENESS_PATH}"' in body


def test_metrics_can_be_disabled(client):
    main.app.dependency_overrides[get_settings] = lambda: Settings(metrics_enabled=False)

    response = client.get(METRICS_PATH)

    assert response.status_code == NOT_FOUND_STATUS


def test_response_carries_a_request_id(client):
    response = client.get(LIVENESS_PATH)

    assert response.headers[REQUEST_ID_HEADER]


def test_caller_supplied_request_id_is_propagated(client):
    response = client.get(LIVENESS_PATH, headers={REQUEST_ID_HEADER: CALLER_REQUEST_ID})

    assert response.headers[REQUEST_ID_HEADER] == CALLER_REQUEST_ID


def test_unmatched_paths_collapse_to_one_metric_label(client):
    client.get(UNKNOWN_PATH)

    body = client.get(METRICS_PATH).text

    assert 'route="unmatched"' in body
    assert UNKNOWN_PATH not in body
