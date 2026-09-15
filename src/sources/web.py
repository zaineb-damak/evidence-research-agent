"""Web connector via Tavily.

Tavily returns clean content + snippets tuned for LLM agents, so we can skip a
separate fetch for the web arm and fall back to the fetcher only when content
is missing.
"""

from __future__ import annotations

from urllib.parse import urlparse

from tavily import TavilyClient

from src.models.schemas import SourceType
from src.sources.base import RawResult, SourceConnector

ADVANCED_SEARCH_DEPTH = "advanced"


class TavilyWebConnector(SourceConnector):
    source_type = SourceType.WEB

    def __init__(self, api_key: str):
        self._client = TavilyClient(api_key=api_key)

    def search(self, query: str, limit: int) -> list[RawResult]:
        response = self._client.search(
            query=query,
            max_results=limit,
            search_depth=ADVANCED_SEARCH_DEPTH,
            include_raw_content=True,
        )
        results: list[RawResult] = []
        for item in response.get("results", []):
            url = item.get("url", "")
            results.append(
                RawResult(
                    url=url,
                    title=item.get("title"),
                    snippet=item.get("content"),
                    content=item.get("raw_content") or item.get("content"),
                    source_type=SourceType.WEB,
                    domain=urlparse(url).netloc,
                )
            )
        return results
