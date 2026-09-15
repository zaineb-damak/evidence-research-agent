"""Reddit / community connector via PRAW (read-only app credentials)."""

from __future__ import annotations

import praw

from src.clock import from_timestamp
from src.models.schemas import SourceType
from src.sources.base import RawResult, SourceConnector

ALL_SUBREDDITS = "all"
SNIPPET_MAX_CHARS = 500


class RedditConnector(SourceConnector):
    source_type = SourceType.REDDIT

    def __init__(
        self,
        client_id: str | None,
        client_secret: str | None,
        user_agent: str,
        base_url: str,
        domain: str,
    ):
        self._enabled = bool(client_id and client_secret)
        self._user_agent = user_agent
        self._base_url = base_url
        self._domain = domain
        if self._enabled:
            self._reddit = praw.Reddit(
                client_id=client_id,
                client_secret=client_secret,
                user_agent=user_agent,
                check_for_async=False,
            )

    def search(self, query: str, limit: int) -> list[RawResult]:
        if not self._enabled:
            return []
        results: list[RawResult] = []
        try:
            for post in self._reddit.subreddit(ALL_SUBREDDITS).search(query, limit=limit):
                body_text = post.selftext or post.title
                results.append(
                    RawResult(
                        url=f"{self._base_url}{post.permalink}",
                        title=post.title,
                        snippet=body_text[:SNIPPET_MAX_CHARS],
                        content=body_text,
                        source_type=SourceType.REDDIT,
                        published_at=from_timestamp(post.created_utc),
                        author=str(post.author),
                        domain=self._domain,
                        extra={"score": post.score, "subreddit": str(post.subreddit)},
                    )
                )
        except Exception:
            return results
        return results
