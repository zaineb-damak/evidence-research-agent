"""robots.txt compliance (§22).

Before fetching a page, check the origin's robots.txt for the configured crawler
user agent and skip disallowed paths rather than working around them. Parsers are
cached per origin. On any failure to retrieve robots.txt, default to allowed
(standard crawler behavior) but never bypass an explicit disallow.
"""

from __future__ import annotations

from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

ROBOTS_PATH = "/robots.txt"

_parsers_by_origin: dict[str, RobotFileParser] = {}


def _origin(url: str) -> str:
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"


def _parser_for(origin: str) -> RobotFileParser:
    cached_parser = _parsers_by_origin.get(origin)
    if cached_parser is not None:
        return cached_parser

    parser = RobotFileParser()
    parser.set_url(urljoin(origin, ROBOTS_PATH))
    try:
        parser.read()
    except Exception:
        # Unreachable robots.txt: treat as no restrictions, the conventional
        # crawler default. An explicit disallow still blocks below.
        parser.parse([])
    _parsers_by_origin[origin] = parser
    return parser


def is_allowed(url: str, user_agent: str) -> bool:
    parser = _parser_for(_origin(url))
    return parser.can_fetch(user_agent, url)
