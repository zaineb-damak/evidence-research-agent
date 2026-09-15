"""Langfuse tracing wiring.

Returns a LangChain callback handler that traces LLM and graph calls into
Langfuse when credentials are configured, and None otherwise so runs stay fully
offline in tests and local development. Attach the returned callbacks to the
structured chains and the LangGraph invoke config.
"""

from __future__ import annotations

from langchain_core.callbacks import BaseCallbackHandler

from src.config import Settings, get_settings


def build_langfuse_handler(settings: Settings | None = None) -> BaseCallbackHandler | None:
    settings = settings or get_settings()
    if not (settings.langfuse_public_key and settings.langfuse_secret_key):
        return None

    # Optional integration; imported lazily so setups without Langfuse keys never
    # need the langfuse SDK resolved at import time. In langfuse v3+ the handler
    # lives in langfuse.langchain and reads credentials from the initialized
    # client, so we construct the client first, then a no-arg handler.
    from langfuse import Langfuse
    from langfuse.langchain import CallbackHandler

    Langfuse(
        public_key=settings.langfuse_public_key,
        secret_key=settings.langfuse_secret_key,
        host=settings.langfuse_host,
    )
    return CallbackHandler()


def langfuse_callbacks(settings: Settings | None = None) -> list[BaseCallbackHandler]:
    """Convenience: the handler as a list ready for an invoke config."""
    handler = build_langfuse_handler(settings)
    return [handler] if handler else []
