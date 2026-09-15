"""Read token usage off a raw LangChain AIMessage for the cost meter.

Structured chains run with `include_raw=True`, so the raw `AIMessage` is
available alongside the parsed model; this helper pulls the input/output token
counts from its `usage_metadata`.
"""

from __future__ import annotations

from langchain_core.messages import AIMessage

INPUT_TOKENS_KEY = "input_tokens"
OUTPUT_TOKENS_KEY = "output_tokens"


def token_usage(raw_message: AIMessage | None) -> tuple[int, int]:
    """Return (tokens_in, tokens_out) from a raw AIMessage; (0, 0) when absent."""
    usage_metadata = getattr(raw_message, "usage_metadata", None) or {}
    tokens_in = usage_metadata.get(INPUT_TOKENS_KEY, 0) or 0
    tokens_out = usage_metadata.get(OUTPUT_TOKENS_KEY, 0) or 0
    return tokens_in, tokens_out
