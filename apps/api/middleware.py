"""Per-request correlation ids, access logging and HTTP metrics.

Written as raw ASGI rather than on Starlette's `BaseHTTPMiddleware` on purpose:
that base class wraps the response body in an anyio stream, which delays the
chunks of the SSE progress endpoint (`GET /api/research/{id}/events`). A pure
ASGI middleware passes every `send` straight through, so live progress stays
live.

Metrics are labelled with the *route template* (`/api/research/{research_id}`),
never the raw path, so one time series does not fan out per research id.
"""

from __future__ import annotations

import time
from uuid import uuid4

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from src.clock import MILLISECONDS_PER_SECOND
from src.observability.logging import (
    REQUEST_ID_FIELD,
    bind_request_context,
    clear_request_context,
    get_logger,
)
from src.observability.metrics import observe_http_request

HTTP_SCOPE_TYPE = "http"
RESPONSE_START_MESSAGE = "http.response.start"

REQUEST_ID_HEADER = "X-Request-ID"

# Label used when no route matched, so a 404 scan cannot create a new metric
# series per path it probes.
UNMATCHED_ROUTE_LABEL = "unmatched"

# Starlette's router records the matched route on the scope while handling the
# request, which is where the path *template* comes from.
ROUTE_SCOPE_KEY = "route"

# Status reported for a request whose handler raised before sending a response.
INTERNAL_ERROR_STATUS = 500

ACCESS_LOG_EVENT = "http_request"

# The kubelet probes liveness/readiness every few seconds and Prometheus scrapes
# constantly; access-logging those would drown the real traffic. They are still
# counted in metrics.
UNLOGGED_ROUTES = frozenset({"/health/live", "/health/ready", "/metrics"})


def _route_template(scope: Scope) -> str:
    """The matched route's path template, for low-cardinality metric labels.

    Only meaningful once the router has handled the request. An unmatched path
    (a 404, including scans) collapses to a single label rather than minting a
    metric series per URL probed.
    """
    matched_route = scope.get(ROUTE_SCOPE_KEY)
    return getattr(matched_route, "path", None) or UNMATCHED_ROUTE_LABEL


class RequestContextMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self._app = app
        self._logger = get_logger(__name__)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != HTTP_SCOPE_TYPE:
            await self._app(scope, receive, send)
            return

        request_id = self._incoming_request_id(scope) or uuid4().hex
        method = scope["method"]
        started_at = time.perf_counter()
        # Mutable because the status is only known once the response starts,
        # which happens inside the nested send wrapper.
        response_status = [INTERNAL_ERROR_STATUS]

        async def send_with_request_id(message: Message) -> None:
            if message["type"] == RESPONSE_START_MESSAGE:
                response_status[0] = message["status"]
                MutableHeaders(scope=message)[REQUEST_ID_HEADER] = request_id
            await send(message)

        clear_request_context()
        bind_request_context(**{REQUEST_ID_FIELD: request_id})
        try:
            await self._app(scope, receive, send_with_request_id)
        finally:
            duration_seconds = time.perf_counter() - started_at
            status_code = response_status[0]
            # Read after handling: the router sets the matched route on the scope.
            route = _route_template(scope)
            observe_http_request(method, route, status_code, duration_seconds)
            if route not in UNLOGGED_ROUTES:
                self._logger.info(
                    ACCESS_LOG_EVENT,
                    method=method,
                    route=route,
                    path=scope["path"],
                    status=status_code,
                    duration_ms=round(duration_seconds * MILLISECONDS_PER_SECOND),
                )
            clear_request_context()

    @staticmethod
    def _incoming_request_id(scope: Scope) -> str | None:
        """Reuse the id an ingress or upstream service already assigned."""
        wanted = REQUEST_ID_HEADER.lower().encode()
        for name, value in scope["headers"]:
            if name.lower() == wanted:
                return value.decode()
        return None
