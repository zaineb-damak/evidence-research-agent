"""Research paper connector via the Semantic Scholar Graph API (no auth)."""

from __future__ import annotations

from datetime import datetime

import httpx

from src.models.schemas import SourceType
from src.sources.base import RawResult, SourceConnector

SEMANTIC_SCHOLAR_DOMAIN = "semanticscholar.org"
PAPER_FIELDS = "title,abstract,url,year,authors,venue"
REQUEST_TIMEOUT_SECONDS = 20.0
USER_AGENT_HEADER = "User-Agent"
SNIPPET_MAX_CHARS = 500
AUTHOR_SEPARATOR = ", "
JANUARY = 1
FIRST_DAY_OF_MONTH = 1


class SemanticScholarConnector(SourceConnector):
    source_type = SourceType.PAPER

    def __init__(self, user_agent: str, search_url: str):
        self._user_agent = user_agent
        self._search_url = search_url

    def search(self, query: str, limit: int) -> list[RawResult]:
        try:
            response = httpx.get(
                self._search_url,
                params={"query": query, "limit": limit, "fields": PAPER_FIELDS},
                headers={USER_AGENT_HEADER: self._user_agent},
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
        except Exception:
            return []

        results: list[RawResult] = []
        for paper in response.json().get("data", []):
            abstract = paper.get("abstract") or ""
            publication_year = paper.get("year")
            published_at = (
                datetime(publication_year, JANUARY, FIRST_DAY_OF_MONTH)
                if publication_year
                else None
            )
            results.append(
                RawResult(
                    url=paper.get("url", ""),
                    title=paper.get("title"),
                    snippet=abstract[:SNIPPET_MAX_CHARS],
                    content=abstract,
                    source_type=SourceType.PAPER,
                    published_at=published_at,
                    author=AUTHOR_SEPARATOR.join(
                        author.get("name", "") for author in paper.get("authors", [])
                    ),
                    domain=SEMANTIC_SCHOLAR_DOMAIN,
                )
            )
        return results
