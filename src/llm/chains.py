"""Build native LangChain structured-output chains.

One place defines the chain shape used by every agent: a prompt template piped
into `chat_model.with_structured_output(schema, include_raw=True)` with retries.
`include_raw=True` yields {"parsed": <schema>, "raw": <AIMessage>, ...} so the
cost meter can read token usage from the raw message (see src/llm/usage.py).
"""

from __future__ import annotations

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable
from pydantic import BaseModel

from src.llm.base import LLMProviderName, StructuredLLM

# LangChain `with_structured_output` extraction methods.
FUNCTION_CALLING = "function_calling"
JSON_MODE = "json_mode"

# Self-hosted OpenAI-compatible models often lack reliable tool/function calling,
# so JSON mode is the safer structured-output path for them.
_METHOD_BY_PROVIDER = {
    LLMProviderName.OPENAI: FUNCTION_CALLING,
    LLMProviderName.ANTHROPIC: FUNCTION_CALLING,
    LLMProviderName.VERTEX: FUNCTION_CALLING,
    LLMProviderName.OAI_COMPAT: JSON_MODE,
}


def structured_output_method(provider: LLMProviderName) -> str:
    """The structured-output method appropriate for a provider."""
    return _METHOD_BY_PROVIDER.get(provider, FUNCTION_CALLING)


def build_structured_chain(
    llm: StructuredLLM, prompt: ChatPromptTemplate, schema: type[BaseModel]
) -> Runnable:
    """Return a chain that maps prompt inputs to {"parsed", "raw", ...}."""
    structured_model = llm.chat_model.with_structured_output(
        schema, include_raw=True, method=llm.method
    )
    # retry_attempts additional tries on top of the first attempt.
    return (prompt | structured_model).with_retry(
        stop_after_attempt=llm.retry_attempts + 1
    )
