"""Redis pub/sub channel naming for live research progress events."""

from __future__ import annotations

PROGRESS_CHANNEL_PREFIX = "research-progress"


def progress_channel_name(research_id: str) -> str:
    return f"{PROGRESS_CHANNEL_PREFIX}:{research_id}"
