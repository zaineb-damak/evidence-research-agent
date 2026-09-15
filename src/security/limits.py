"""Resource limits for untrusted content (§22).

Bounds on document/page size, source counts, and crawl recursion so a single
job cannot exhaust memory or run away. These are hard ceilings that sit above
the per-tier depth caps in config.py.
"""

from __future__ import annotations

MAX_PAGE_BYTES = 5_000_000  # 5 MB downloaded per page
MAX_DOCUMENT_CHARS = 200_000  # kept after cleaning
MAX_SOURCES_HARD_CAP = 100  # absolute ceiling regardless of depth tier
MAX_CRAWL_RECURSION_DEPTH = 2


def truncate_document(text: str, max_chars: int = MAX_DOCUMENT_CHARS) -> str:
    return text[:max_chars]


def within_source_cap(current_source_count: int) -> bool:
    return current_source_count < MAX_SOURCES_HARD_CAP


def within_recursion_depth(depth: int) -> bool:
    return depth <= MAX_CRAWL_RECURSION_DEPTH
