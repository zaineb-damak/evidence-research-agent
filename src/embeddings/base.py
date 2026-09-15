"""Embedding provider selection.

Phase 8 dropped the custom `Embedder` wrapper; callers use LangChain's
`Embeddings` interface (`embed_documents` / `embed_query`) directly, and the
embedding dimension comes from settings (`embed_dim`). This module keeps only the
provider enum used by config and the factory.
"""

from __future__ import annotations

from enum import StrEnum


class EmbeddingProviderName(StrEnum):
    OPENAI = "openai"
    VOYAGE = "voyage"
