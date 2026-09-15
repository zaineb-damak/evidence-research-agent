"""Lightweight PII redaction for retrieved content (§22).

Retrieved pages are untrusted and may contain personal data. We redact obvious
identifiers (emails, phone numbers) before the text is stored or placed in a
prompt. This is a pragmatic filter, not a compliance-grade PII engine.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

EMAIL_PLACEHOLDER = "[REDACTED_EMAIL]"
PHONE_PLACEHOLDER = "[REDACTED_PHONE]"

EMAIL_PATTERN = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
# Loose international phone match: optional +, groups of digits with separators.
PHONE_PATTERN = re.compile(r"\+?\d[\d\s().-]{7,}\d")


@dataclass
class RedactionResult:
    text: str
    emails_redacted: int
    phones_redacted: int


def redact_pii(text: str) -> RedactionResult:
    redacted_text, email_count = EMAIL_PATTERN.subn(EMAIL_PLACEHOLDER, text)
    redacted_text, phone_count = PHONE_PATTERN.subn(PHONE_PLACEHOLDER, redacted_text)
    return RedactionResult(
        text=redacted_text,
        emails_redacted=email_count,
        phones_redacted=phone_count,
    )
