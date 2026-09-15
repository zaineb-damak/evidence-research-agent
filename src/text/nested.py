"""Helpers for reading values out of nested dictionaries."""

from __future__ import annotations

from typing import Any

PATH_SEPARATOR = "."


def dig_nested(obj: dict, dotted_path: str) -> Any | None:
    """Walk a dotted path (e.g. "data.results") into a nested dict.

    Returns None if any segment is missing or a non-dict is encountered.
    """
    current: Any = obj
    for segment in dotted_path.split(PATH_SEPARATOR):
        if not isinstance(current, dict):
            return None
        current = current.get(segment)
    return current
