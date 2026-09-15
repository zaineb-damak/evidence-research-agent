"""Select and initialize a LangChain Embeddings object from settings."""

from __future__ import annotations

from langchain_core.embeddings import Embeddings
from langchain_openai import OpenAIEmbeddings

from src.config import Settings, get_settings
from src.embeddings.base import EmbeddingProviderName
from src.exceptions import ProviderConfigError, UnknownProviderError

EMBED_PROVIDER_SETTING = "EMBED_PROVIDER"
OPENAI_KEY_NAME = "OPENAI_API_KEY"
VOYAGE_KEY_NAME = "VOYAGE_API_KEY"


def build_embedder(settings: Settings | None = None) -> Embeddings:
    settings = settings or get_settings()
    provider = settings.embed_provider

    if provider == EmbeddingProviderName.OPENAI:
        if not settings.openai_api_key:
            raise ProviderConfigError(OPENAI_KEY_NAME, EMBED_PROVIDER_SETTING, provider)
        return OpenAIEmbeddings(
            model=settings.embed_model,
            dimensions=settings.embed_dim,
            api_key=settings.openai_api_key,
        )

    if provider == EmbeddingProviderName.VOYAGE:
        if not settings.voyage_api_key:
            raise ProviderConfigError(VOYAGE_KEY_NAME, EMBED_PROVIDER_SETTING, provider)
        # Optional integration package; imported lazily so OpenAI-only setups
        # never need langchain-voyageai installed.
        from langchain_voyageai import VoyageAIEmbeddings

        return VoyageAIEmbeddings(
            model=settings.embed_model,
            api_key=settings.voyage_api_key,
        )

    raise UnknownProviderError(EMBED_PROVIDER_SETTING, provider)
