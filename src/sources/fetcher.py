"""Fetch and clean page content into plain text, then chunk into passages.

Retrieved content is untrusted data — never merged into system prompts (see
src/security/injection.py). Fetching is hardened (§22): SSRF is re-checked on
every redirect hop, robots.txt is honored, page size is capped, and obvious PII
is redacted from the cleaned text.
"""

from __future__ import annotations

import re

import httpx
import trafilatura
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.security.limits import MAX_PAGE_BYTES
from src.security.robots import is_allowed
from src.security.sanitize import sanitize_document_text
from src.security.url_guard import is_safe_url

CHUNK_CHARS = 1_200
CHUNK_OVERLAP_CHARS = 150
DEFAULT_FETCH_TIMEOUT_SECONDS = 15.0
MAX_REDIRECT_HOPS = 5
USER_AGENT_HEADER = "User-Agent"
LOCATION_HEADER = "location"
REDIRECT_STATUS_MIN = 300
REDIRECT_STATUS_MAX = 400

# LangChain splitter reused across calls; splits on paragraph/sentence/word
# boundaries before falling back to a hard character cut.
_text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=CHUNK_CHARS,
    chunk_overlap=CHUNK_OVERLAP_CHARS,
)


def _fetch_following_redirects_safely(
    url: str, user_agent: str, timeout_seconds: float
) -> httpx.Response | None:
    """Fetch a URL, re-validating SSRF safety and robots on every redirect hop.

    Auto-following redirects can bypass an SSRF check when a public URL redirects
    to an internal address, so each hop is validated explicitly.
    """
    current_url = url
    with httpx.Client(follow_redirects=False, timeout=timeout_seconds) as client:
        for _hop in range(MAX_REDIRECT_HOPS):
            if not is_safe_url(current_url):
                return None
            if not is_allowed(current_url, user_agent):
                return None
            response = client.get(current_url, headers={USER_AGENT_HEADER: user_agent})
            is_redirect = REDIRECT_STATUS_MIN <= response.status_code < REDIRECT_STATUS_MAX
            if is_redirect and LOCATION_HEADER in response.headers:
                current_url = str(response.url.join(response.headers[LOCATION_HEADER]))
                continue
            return response
    return None


def fetch_clean(
    url: str, user_agent: str, timeout_seconds: float = DEFAULT_FETCH_TIMEOUT_SECONDS
) -> str | None:
    """Fetch a URL and extract cleaned, PII-redacted main-content text."""
    try:
        response = _fetch_following_redirects_safely(url, user_agent, timeout_seconds)
        if response is None:
            return None
        response.raise_for_status()
    except Exception:
        return None

    if len(response.content) > MAX_PAGE_BYTES:
        return None

    extracted_text = trafilatura.extract(response.text, include_comments=False) or ""
    if not extracted_text:
        return None
    return sanitize_document_text(extracted_text) or None


def chunk_text(text: str) -> list[str]:
    """Split cleaned text into overlapping passages via LangChain's splitter."""
    normalized_text = re.sub(r"\s+", " ", text).strip()
    if not normalized_text:
        return []
    return [chunk.strip() for chunk in _text_splitter.split_text(normalized_text) if chunk.strip()]
