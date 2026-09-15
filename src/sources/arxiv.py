"""arXiv connector via the public Atom API (no auth required)."""

from __future__ import annotations

from datetime import datetime

import feedparser
import httpx

from src.models.schemas import SourceType
from src.sources.base import RawResult, SourceConnector

RELEVANCE_SORT = "relevance"
REQUEST_TIMEOUT_SECONDS = 20.0
USER_AGENT_HEADER = "User-Agent"
AUTHOR_SEPARATOR = ", "


class ArxivConnector(SourceConnector):
    source_type = SourceType.ARXIV

    def __init__(self, user_agent: str, api_url: str, domain: str):
        self._user_agent = user_agent
        self._api_url = api_url
        self._domain = domain

    def search(self, query: str, limit: int) -> list[RawResult]:
        try:
            response = httpx.get(
                self._api_url,
                params={
                    "search_query": f"all:{query}",
                    "start": 0,
                    "max_results": limit,
                    "sortBy": RELEVANCE_SORT,
                },
                headers={USER_AGENT_HEADER: self._user_agent},
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
        except Exception:
            return []

        feed = feedparser.parse(response.text)
        results: list[RawResult] = []
        for entry in feed.entries:
            published_at = None
            if getattr(entry, "published_parsed", None):
                published_at = datetime(*entry.published_parsed[:6])
            summary = entry.get("summary", "").strip()
            results.append(
                RawResult(
                    url=entry.get("link", ""),
                    title=entry.get("title", "").strip(),
                    snippet=summary,
                    content=summary,
                    source_type=SourceType.ARXIV,
                    published_at=published_at,
                    author=AUTHOR_SEPARATOR.join(
                        author.name for author in getattr(entry, "authors", [])
                    ),
                    domain=self._domain,
                )
            )
        return results
