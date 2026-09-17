"""Redis pub/sub transport for ProgressEvents.

The worker publishes with a cached synchronous `redis.Redis` client
(`publish_progress_event`); the FastAPI SSE route subscribes with
`redis.asyncio` (`subscribe_to_progress`). No new dependency — `redis` (which
ships both a sync and an asyncio client) is already a direct dependency.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from functools import lru_cache

import redis
import redis.asyncio as redis_asyncio

from src.config import Settings
from src.models.progress import ProgressEvent
from src.realtime.channels import progress_channel_name

PUBSUB_MESSAGE_TYPE = "message"


@lru_cache
def _sync_redis_client(redis_url: str) -> redis.Redis:
    return redis.Redis.from_url(redis_url)


def publish_progress_event(event: ProgressEvent, settings: Settings) -> None:
    client = _sync_redis_client(settings.redis_url)
    client.publish(progress_channel_name(event.research_id), event.model_dump_json())


async def subscribe_to_progress(
    research_id: str, settings: Settings
) -> AsyncIterator[ProgressEvent]:
    """Yield ProgressEvents published on `research_id`'s channel as they arrive."""
    client = redis_asyncio.Redis.from_url(settings.redis_url)
    pubsub = client.pubsub()
    channel_name = progress_channel_name(research_id)
    try:
        await pubsub.subscribe(channel_name)
        async for message in pubsub.listen():
            if message["type"] != PUBSUB_MESSAGE_TYPE:
                continue
            yield ProgressEvent.model_validate_json(message["data"])
    finally:
        await pubsub.unsubscribe(channel_name)
        await pubsub.aclose()
        await client.aclose()
