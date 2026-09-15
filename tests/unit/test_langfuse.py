"""Langfuse handler: off by default, constructible when keys are present."""

from __future__ import annotations

from src.config import Settings
from src.observability.langfuse import build_langfuse_handler, langfuse_callbacks


def test_handler_is_none_without_keys():
    assert build_langfuse_handler(Settings()) is None
    assert langfuse_callbacks(Settings()) == []


def test_handler_built_when_keys_present():
    settings = Settings(langfuse_public_key="pk-test", langfuse_secret_key="sk-test")
    handler = build_langfuse_handler(settings)
    assert handler is not None
    assert langfuse_callbacks(settings) == [handler] or len(langfuse_callbacks(settings)) == 1
