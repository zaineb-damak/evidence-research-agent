"""Generic configurable REST API connector.

Lets an operator plug an arbitrary JSON search endpoint into the pipeline by
describing where results, url, title, and content live in the response. Kept
generic so no single vendor is baked in.
"""

from __future__ import annotations

from dataclasses import dataclass

import httpx

from src.models.schemas import SourceType
from src.sources.base import RawResult, SourceConnector
from src.text.nested import dig_nested

DEFAULT_QUERY_PARAM = "q"
DEFAULT_RESULTS_PATH = "results"
DEFAULT_URL_FIELD = "url"
DEFAULT_TITLE_FIELD = "title"
DEFAULT_CONTENT_FIELD = "content"
REQUEST_TIMEOUT_SECONDS = 20.0
USER_AGENT_HEADER = "User-Agent"


@dataclass
class ApiConfig:
    endpoint: str
    query_param: str = DEFAULT_QUERY_PARAM
    results_path: str = DEFAULT_RESULTS_PATH  # dotted path to the results list
    url_field: str = DEFAULT_URL_FIELD
    title_field: str = DEFAULT_TITLE_FIELD
    content_field: str = DEFAULT_CONTENT_FIELD
    headers: dict | None = None


class GenericApiConnector(SourceConnector):
    source_type = SourceType.API

    def __init__(self, config: ApiConfig, user_agent: str):
        self._config = config
        self._user_agent = user_agent

    def search(self, query: str, limit: int) -> list[RawResult]:
        request_headers = {USER_AGENT_HEADER: self._user_agent, **(self._config.headers or {})}
        try:
            response = httpx.get(
                self._config.endpoint,
                params={self._config.query_param: query},
                headers=request_headers,
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
        except Exception:
            return []

        items = dig_nested(response.json(), self._config.results_path) or []
        results: list[RawResult] = []
        for item in items[:limit]:
            if not isinstance(item, dict):
                continue
            results.append(
                RawResult(
                    url=item.get(self._config.url_field, ""),
                    title=item.get(self._config.title_field),
                    content=item.get(self._config.content_field),
                    source_type=SourceType.API,
                )
            )
        return results
