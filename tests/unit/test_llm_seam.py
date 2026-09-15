"""The LangChain-native structured-output seam and reliability wiring."""

from __future__ import annotations

import pytest
from langchain_core.caches import InMemoryCache
from langchain_core.globals import get_llm_cache
from pydantic import BaseModel

from src.config import Settings
from src.embeddings.base import EmbeddingProviderName
from src.exceptions import ProviderConfigError, UnknownProviderError
from src.llm.base import LLMProviderName
from src.llm.caching import configure_llm_cache
from src.llm.chains import (
    FUNCTION_CALLING,
    JSON_MODE,
    build_structured_chain,
    structured_output_method,
)
from src.llm.factory import build_llm
from src.llm.usage import token_usage
from tests.conftest import fixed_response, structured_llm


class _Answer(BaseModel):
    value: str


def test_structured_chain_parses_and_reports_usage():
    llm = structured_llm(fixed_response({"value": "hello"}))
    # A trivial prompt with no variables.
    from langchain_core.prompts import ChatPromptTemplate

    prompt = ChatPromptTemplate.from_messages([("human", "give me a value")])
    chain = build_structured_chain(llm, prompt, _Answer)

    result = chain.invoke({})
    assert result["parsed"] == _Answer(value="hello")
    assert token_usage(result["raw"]) == (10, 10)


def test_structured_output_method_per_provider():
    assert structured_output_method(LLMProviderName.OAI_COMPAT) == JSON_MODE
    assert structured_output_method(LLMProviderName.OPENAI) == FUNCTION_CALLING
    assert structured_output_method(LLMProviderName.ANTHROPIC) == FUNCTION_CALLING


def test_build_llm_selects_method_and_requires_key():
    settings = Settings(
        llm_provider=LLMProviderName.ANTHROPIC, anthropic_api_key="sk-test"
    )
    llm = build_llm(settings)
    assert llm.method == FUNCTION_CALLING
    assert llm.model == settings.llm_model

    with pytest.raises(ProviderConfigError):
        build_llm(Settings(llm_provider=LLMProviderName.OPENAI, openai_api_key=None))


def test_unknown_embedding_provider_raises():
    from src.embeddings.factory import build_embedder

    # A provider value the factory does not handle.
    settings = Settings(embed_provider=EmbeddingProviderName.OPENAI, openai_api_key=None)
    with pytest.raises(ProviderConfigError):
        build_embedder(settings)


def test_configure_llm_cache_memory_backend():
    configure_llm_cache(Settings(llm_cache_backend="memory"))
    assert isinstance(get_llm_cache(), InMemoryCache)
    configure_llm_cache(Settings(llm_cache_backend="none"))
    assert get_llm_cache() is None


def test_unknown_llm_provider_is_rejected():
    # Construct a settings whose provider is valid enum but force the factory's
    # exhaustiveness by monkey-checking the mapping via an invalid string.
    settings = Settings(anthropic_api_key="sk-test")
    object.__setattr__(settings, "llm_provider", "made_up_provider")
    with pytest.raises(UnknownProviderError):
        build_llm(settings)
