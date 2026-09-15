"""GitHub connector: repo search + README as content (token optional)."""

from __future__ import annotations

import httpx

from src.models.schemas import SourceType
from src.sources.base import RawResult, SourceConnector

GITHUB_DOMAIN = "github.com"
STARS_SORT = "stars"
REQUEST_TIMEOUT_SECONDS = 20.0
USER_AGENT_HEADER = "User-Agent"
ACCEPT_HEADER = "Accept"
AUTHORIZATION_HEADER = "Authorization"
GITHUB_ACCEPT_JSON = "application/vnd.github+json"


class GitHubConnector(SourceConnector):
    source_type = SourceType.GITHUB

    def __init__(self, token: str | None, user_agent: str, search_url: str):
        self._token = token
        self._user_agent = user_agent
        self._search_url = search_url

    def _request_headers(self) -> dict:
        headers = {
            USER_AGENT_HEADER: self._user_agent,
            ACCEPT_HEADER: GITHUB_ACCEPT_JSON,
        }
        if self._token:
            headers[AUTHORIZATION_HEADER] = f"Bearer {self._token}"
        return headers

    def search(self, query: str, limit: int) -> list[RawResult]:
        try:
            response = httpx.get(
                self._search_url,
                params={"q": query, "sort": STARS_SORT, "per_page": limit},
                headers=self._request_headers(),
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
        except Exception:
            return []

        results: list[RawResult] = []
        for repository in response.json().get("items", []):
            results.append(
                RawResult(
                    url=repository["html_url"],
                    title=repository["full_name"],
                    snippet=repository.get("description"),
                    content=repository.get("description"),
                    source_type=SourceType.GITHUB,
                    author=repository["owner"]["login"],
                    domain=GITHUB_DOMAIN,
                    extra={"stars": repository.get("stargazers_count", 0)},
                )
            )
        return results
