"""Lowercase alphanumeric tokenizer for the in-memory keyword scorer."""

from __future__ import annotations

import re

_TOKEN = re.compile(r"[a-z0-9]+")


def tokens(text: str) -> list[str]:
    return _TOKEN.findall(text.lower())
