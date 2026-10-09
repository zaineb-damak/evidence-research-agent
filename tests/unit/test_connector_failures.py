"""A connector that fails open must still leave a trace: a metric and a reason."""

from __future__ import annotations

import httpx
import pytest

from src.observability.metrics import SOURCE_CONNECTOR_FAILURES_TOTAL
from src.sources import papers
from src.sources.failures import failure_reason
from src.sources.papers import SemanticScholarConnector

SEARCH_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
TOO_MANY_REQUESTS = 429


def _failure_count(connector: str, reason: str) -> float:
    return SOURCE_CONNECTOR_FAILURES_TOTAL.labels(connector=connector, reason=reason)._value.get()


def _rate_limited_get(url, **_kwargs):
    request = httpx.Request("GET", url)
    return httpx.Response(TOO_MANY_REQUESTS, request=request)


def test_reason_is_the_http_status_for_status_errors():
    request = httpx.Request("GET", SEARCH_URL)
    error = httpx.HTTPStatusError(
        "rate limited", request=request, response=httpx.Response(TOO_MANY_REQUESTS, request=request)
    )
    assert failure_reason(error) == str(TOO_MANY_REQUESTS)


def test_reason_is_the_error_type_otherwise():
    assert failure_reason(httpx.ConnectTimeout("slow")) == "ConnectTimeout"


def test_rate_limited_paper_search_fails_open_but_is_counted(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(papers.httpx, "get", _rate_limited_get)
    connector = SemanticScholarConnector(user_agent="test-agent", search_url=SEARCH_URL)
    before = _failure_count("paper", str(TOO_MANY_REQUESTS))

    results = connector.search("retrieval-augmented generation", limit=3)

    assert results == []
    assert _failure_count("paper", str(TOO_MANY_REQUESTS)) == before + 1
