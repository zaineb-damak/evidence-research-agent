"""Provider-agnostic LLM value types.

Phase 8 removed the hand-rolled `complete()` seam and JSON-parse-retry loop in
favor of native LangChain chains (see src/llm/chains.py). What remains here is
the provider enum and a thin, logic-free value object bundling a LangChain chat
model with the structured-output settings a chain needs. No wrapping behavior
lives on it — chain construction and token accounting are native LangChain.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from langchain_core.language_models import BaseChatModel


class LLMProviderName(StrEnum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    VERTEX = "vertex"
    OAI_COMPAT = "oai_compat"


@dataclass(frozen=True)
class StructuredLLM:
    """A configured chat model plus how to coax structured output from it.

    `method` is the LangChain `with_structured_output` method appropriate for the
    provider (function calling vs JSON mode); `retry_attempts` feeds
    `Runnable.with_retry`. `model` is the model id, kept for the cost meter.
    """

    chat_model: BaseChatModel
    model: str
    method: str
    retry_attempts: int
