"""Common connector interface. Every source type implements SourceConnector."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol, runtime_checkable

from src.models.schemas import SourceType


@dataclass
class RawResult:
    """What a connector returns before fetching/cleaning full content."""

    url: str
    title: str | None = None
    snippet: str | None = None
    content: str | None = None  # some connectors return full text directly
    source_type: SourceType = SourceType.WEB
    published_at: datetime | None = None
    author: str | None = None
    domain: str | None = None
    extra: dict = field(default_factory=dict)


@runtime_checkable
class SourceConnector(Protocol):
    source_type: SourceType

    def search(self, query: str, limit: int) -> list[RawResult]: ...
