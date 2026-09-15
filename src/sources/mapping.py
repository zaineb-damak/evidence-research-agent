"""Map connector results into domain models.

Kept apart from the researcher orchestration so the conversion has one home
(CLAUDE.md rule 6).
"""

from __future__ import annotations

from urllib.parse import urlparse

from src.clock import utcnow
from src.models.schemas import Source
from src.sources.base import RawResult


def source_from_raw_result(raw_result: RawResult) -> Source:
    return Source(
        url=raw_result.url,
        title=raw_result.title,
        domain=raw_result.domain or (urlparse(raw_result.url).netloc or None),
        source_type=raw_result.source_type,
        published_at=raw_result.published_at,
        retrieved_at=utcnow(),
        author=raw_result.author,
    )
