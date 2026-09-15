"""Select and initialize a chat model via LangChain's init_chat_model.

Returns a StructuredLLM: the LangChain chat model plus the structured-output
method and retry count that native chains need (src/llm/chains.py). A LangChain
InMemoryRateLimiter is attached to the model when a positive request rate is
configured. No provider is hard-coded as default.
"""

from __future__ import annotations

from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel
from langchain_core.rate_limiters import InMemoryRateLimiter

from src.config import Settings, get_settings
from src.exceptions import ProviderConfigError, UnknownProviderError
from src.llm.base import LLMProviderName, StructuredLLM
from src.llm.chains import structured_output_method

# Our provider names -> LangChain model_provider identifiers.
OPENAI_MODEL_PROVIDER = "openai"
ANTHROPIC_MODEL_PROVIDER = "anthropic"
VERTEX_MODEL_PROVIDER = "google_vertexai"

LLM_PROVIDER_SETTING = "LLM_PROVIDER"
OPENAI_KEY_NAME = "OPENAI_API_KEY"
ANTHROPIC_KEY_NAME = "ANTHROPIC_API_KEY"
VERTEX_PROJECT_NAME = "GOOGLE_CLOUD_PROJECT"

# InMemoryRateLimiter checks this often for available capacity.
RATE_LIMITER_CHECK_SECONDS = 0.1


def build_llm(settings: Settings | None = None) -> StructuredLLM:
    settings = settings or get_settings()
    chat_model = _init_chat_model(settings.llm_provider, settings)
    return StructuredLLM(
        chat_model=chat_model,
        model=settings.llm_model,
        method=structured_output_method(settings.llm_provider),
        retry_attempts=settings.llm_structured_retry_attempts,
    )


def _build_rate_limiter(settings: Settings) -> InMemoryRateLimiter | None:
    if settings.llm_requests_per_second <= 0:
        return None
    return InMemoryRateLimiter(
        requests_per_second=settings.llm_requests_per_second,
        check_every_n_seconds=RATE_LIMITER_CHECK_SECONDS,
    )


def _init_chat_model(provider: LLMProviderName, settings: Settings) -> BaseChatModel:
    rate_limiter = _build_rate_limiter(settings)

    if provider == LLMProviderName.OPENAI:
        if not settings.openai_api_key:
            raise ProviderConfigError(OPENAI_KEY_NAME, LLM_PROVIDER_SETTING, provider)
        return init_chat_model(
            settings.llm_model,
            model_provider=OPENAI_MODEL_PROVIDER,
            api_key=settings.openai_api_key,
            rate_limiter=rate_limiter,
        )

    if provider == LLMProviderName.OAI_COMPAT:
        # Self-hosted / OpenAI-compatible endpoint (Ollama, vLLM, ...).
        return init_chat_model(
            settings.llm_model,
            model_provider=OPENAI_MODEL_PROVIDER,
            api_key=settings.oai_compat_api_key,
            base_url=settings.oai_compat_base_url,
            rate_limiter=rate_limiter,
        )

    if provider == LLMProviderName.ANTHROPIC:
        if not settings.anthropic_api_key:
            raise ProviderConfigError(ANTHROPIC_KEY_NAME, LLM_PROVIDER_SETTING, provider)
        return init_chat_model(
            settings.llm_model,
            model_provider=ANTHROPIC_MODEL_PROVIDER,
            api_key=settings.anthropic_api_key,
            rate_limiter=rate_limiter,
        )

    if provider == LLMProviderName.VERTEX:
        if not settings.google_cloud_project:
            raise ProviderConfigError(VERTEX_PROJECT_NAME, LLM_PROVIDER_SETTING, provider)
        return init_chat_model(
            settings.llm_model,
            model_provider=VERTEX_MODEL_PROVIDER,
            project=settings.google_cloud_project,
            location=settings.google_cloud_location,
            rate_limiter=rate_limiter,
        )

    raise UnknownProviderError(LLM_PROVIDER_SETTING, provider)
