"""Sanitize untrusted document text before it is stored or prompted.

Combines the size cap and PII redaction so every path that ingests external text
(direct fetch and connector-provided content) applies the same treatment.
"""

from __future__ import annotations

from src.security.limits import MAX_DOCUMENT_CHARS, truncate_document
from src.security.pii import redact_pii


def sanitize_document_text(text: str, max_chars: int = MAX_DOCUMENT_CHARS) -> str:
    # Redact before truncating so the placeholder expansion cannot push the
    # result past the size cap.
    redacted_text = redact_pii(text).text
    return truncate_document(redacted_text, max_chars)
