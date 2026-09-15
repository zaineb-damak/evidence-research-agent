"""Build the set of connectors for a request's source types.

Connectors that need missing credentials are simply omitted (they return empty
results rather than raising), so a partial key set still produces a run.
"""

from __future__ import annotations

from src.config import Settings, get_settings
from src.models.schemas import SourceType
from src.sources.arxiv import ArxivConnector
from src.sources.base import SourceConnector
from src.sources.github import GitHubConnector
from src.sources.papers import SemanticScholarConnector
from src.sources.reddit import RedditConnector
from src.sources.web import TavilyWebConnector

# Source types the Tavily web connector serves (documentation is fetched as web).
TAVILY_SERVED_TYPES = (SourceType.WEB, SourceType.DOCUMENTATION)


def build_connectors(
    source_types: list[SourceType], settings: Settings | None = None
) -> dict[SourceType, SourceConnector]:
    settings = settings or get_settings()
    connectors: dict[SourceType, SourceConnector] = {}

    for source_type in source_types:
        if source_type in TAVILY_SERVED_TYPES and settings.tavily_api_key:
            connectors[source_type] = TavilyWebConnector(api_key=settings.tavily_api_key)
        elif source_type == SourceType.PAPER:
            connectors[source_type] = SemanticScholarConnector(
                user_agent=settings.crawler_user_agent,
                search_url=settings.semantic_scholar_search_url,
            )
        elif source_type == SourceType.ARXIV:
            connectors[source_type] = ArxivConnector(
                user_agent=settings.crawler_user_agent,
                api_url=settings.arxiv_api_url,
                domain=settings.arxiv_domain,
            )
        elif source_type == SourceType.GITHUB:
            connectors[source_type] = GitHubConnector(
                token=settings.github_token,
                user_agent=settings.crawler_user_agent,
                search_url=settings.github_search_url,
            )
        elif source_type == SourceType.REDDIT:
            connectors[source_type] = RedditConnector(
                client_id=settings.reddit_client_id,
                client_secret=settings.reddit_client_secret,
                user_agent=settings.reddit_user_agent,
                base_url=settings.reddit_base_url,
                domain=settings.reddit_domain,
            )
        # SourceType.YOUTUBE / API are opt-in with explicit config; skipped by default.

    return connectors
