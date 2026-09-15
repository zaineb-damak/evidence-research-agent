"""Configure LangChain's global LLM cache from settings.

Uses LangChain's built-in cache backends rather than a hand-rolled cache: an
in-process cache by default, or a Redis-backed one for cross-worker reuse.
Call `configure_llm_cache` once at process startup (API and worker).
"""

from __future__ import annotations

from langchain_core.caches import InMemoryCache
from langchain_core.globals import set_llm_cache

from src.config import Settings, get_settings

CACHE_MEMORY = "memory"
CACHE_REDIS = "redis"
CACHE_NONE = "none"


def configure_llm_cache(settings: Settings | None = None) -> None:
    settings = settings or get_settings()
    backend = settings.llm_cache_backend

    if backend == CACHE_NONE:
        set_llm_cache(None)
        return
    if backend == CACHE_REDIS:
        # Optional integration; imported lazily so an in-memory setup never needs
        # the (deprecated) langchain-community package resolved at import time.
        from langchain_community.cache import RedisCache
        from redis import Redis

        set_llm_cache(RedisCache(redis_=Redis.from_url(settings.redis_url)))
        return
    set_llm_cache(InMemoryCache())
