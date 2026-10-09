"""Liveness, readiness and metrics endpoints.

These routes are the documented exception to "every route requires auth" (see
CLAUDE.md): the kubelet cannot present a JWT when probing a pod, and Prometheus
scrapes without a user identity. They expose no research data — only process
state and aggregate counters — and the Ingress never routes to them, so they are
reachable only from inside the cluster.

Liveness answers "is this process wedged"; it must not touch a backing service,
or a database blip would restart every pod. Readiness answers "can this process
serve a request right now" and probes the dependencies a request actually needs.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response
from fastapi.responses import JSONResponse

from apps.api.dependencies import ReadinessChecker, get_readiness_checker
from src.config import Settings, get_settings
from src.observability.metrics import render_latest

LIVENESS_PATH = "/health/live"
READINESS_PATH = "/health/ready"
METRICS_PATH = "/metrics"

HEALTH_TAG = "health"
ALIVE_PAYLOAD = {"status": "alive"}

SERVICE_UNAVAILABLE_STATUS = 503
METRICS_DISABLED_PAYLOAD = {"detail": "metrics are disabled"}
METRICS_DISABLED_STATUS = 404

router = APIRouter(tags=[HEALTH_TAG])


@router.get(LIVENESS_PATH)
def liveness() -> dict:
    """Process is up and the event loop is turning. No dependencies consulted."""
    return ALIVE_PAYLOAD


@router.get(READINESS_PATH)
def readiness(
    response: Response,
    settings: Settings = Depends(get_settings),
    check: ReadinessChecker = Depends(get_readiness_checker),
) -> dict:
    report = check(settings)
    if not report.ready:
        response.status_code = SERVICE_UNAVAILABLE_STATUS
    return report.as_dict()


@router.get(METRICS_PATH)
def metrics(settings: Settings = Depends(get_settings)) -> Response:
    if not settings.metrics_enabled:
        return JSONResponse(METRICS_DISABLED_PAYLOAD, status_code=METRICS_DISABLED_STATUS)
    payload, content_type = render_latest()
    return Response(content=payload, media_type=content_type)
