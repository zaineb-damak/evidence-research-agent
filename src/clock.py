"""Time helpers. Naive UTC everywhere for internal consistency (connectors emit
naive datetimes), using the non-deprecated path."""

from __future__ import annotations

from datetime import UTC, datetime


def utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def from_timestamp(ts: float) -> datetime:
    return datetime.fromtimestamp(ts, UTC).replace(tzinfo=None)
