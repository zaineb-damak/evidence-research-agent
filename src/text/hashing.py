"""Content hashing for idempotent dedup.

Keys derived from content let a restarted worker skip documents it already
processed.
"""

from __future__ import annotations

import hashlib

ENCODING = "utf-8"


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode(ENCODING)).hexdigest()
