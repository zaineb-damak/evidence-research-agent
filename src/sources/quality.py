"""Source quality scoring (§6).

score = authority + recency + relevance + primary_source_bonus + corroboration,
each a measurable component normalized so the total lands in 0..1. Low-quality
sources are scored low, not discarded — the report says so instead.
"""

from __future__ import annotations

from datetime import datetime

from src.clock import utcnow
from src.models.schemas import Source, SourceQuality, SourceType

# Authority prior by source type (0..1).
_AUTHORITY: dict[SourceType, float] = {
    SourceType.DOCUMENTATION: 1.0,
    SourceType.PAPER: 0.95,
    SourceType.ARXIV: 0.85,
    SourceType.API: 0.8,
    SourceType.GITHUB: 0.7,
    SourceType.WEB: 0.5,
    SourceType.YOUTUBE: 0.4,
    SourceType.REDDIT: 0.25,
}

_PRIMARY: set[SourceType] = {
    SourceType.DOCUMENTATION,
    SourceType.PAPER,
    SourceType.ARXIV,
}

# Component weights sum to 1.0.
_W = {
    "authority": 0.35,
    "recency": 0.15,
    "relevance": 0.25,
    "primary": 0.10,
    "corroboration": 0.15,
}


def _recency_score(published_at: datetime | None) -> float:
    if not published_at:
        return 0.5  # unknown → neutral
    age_days = (utcnow() - published_at).days
    if age_days <= 180:
        return 1.0
    if age_days >= 5 * 365:
        return 0.1
    # linear decay between 6 months and 5 years
    return max(0.1, 1.0 - (age_days - 180) / (5 * 365 - 180))


def score_source(
    source: Source, relevance: float, corroboration_count: int
) -> SourceQuality:
    authority = _AUTHORITY.get(source.source_type, 0.4)
    recency = _recency_score(source.published_at)
    relevance = max(0.0, min(1.0, relevance))
    primary = 1.0 if source.source_type in _PRIMARY else 0.0
    corroboration = min(corroboration_count / 3.0, 1.0)

    total = (
        _W["authority"] * authority
        + _W["recency"] * recency
        + _W["relevance"] * relevance
        + _W["primary"] * primary
        + _W["corroboration"] * corroboration
    )
    return SourceQuality(
        authority=authority,
        recency=recency,
        relevance=relevance,
        primary_source_bonus=primary,
        corroboration=corroboration,
        score=round(total, 4),
    )
