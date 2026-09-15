"""Centralized settings and research depth tiers.

All provider selection, service URLs, keys, and cost/latency caps live here so
the rest of the codebase never reads os.environ directly.

Hybrid config: `python-decouple` reads raw environment values (checking the
process environment then a local .env), and `get_settings()` feeds them into a
validated pydantic `Settings` model. Constructing `Settings(...)` directly (as
tests do) bypasses the environment and uses defaults plus overrides, keeping
tests deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from decouple import config
from pydantic import BaseModel

from src.embeddings.base import EmbeddingProviderName
from src.llm.base import LLMProviderName
from src.models.schemas import ResearchDepth


@dataclass(frozen=True)
class DepthCap:
    """Per-tier caps that bound cost and latency for a research job (§18)."""

    max_sources: int
    max_claims: int
    max_sub_questions: int


DEFAULT_DEPTH = ResearchDepth.FAST

# Get the pipeline correct at `fast` first, then raise caps as reliability hardens.
DEPTH_CAPS: dict[ResearchDepth, DepthCap] = {
    ResearchDepth.FAST: DepthCap(max_sources=10, max_claims=25, max_sub_questions=5),
    ResearchDepth.NORMAL: DepthCap(max_sources=25, max_claims=50, max_sub_questions=8),
    ResearchDepth.DEEP: DepthCap(max_sources=50, max_claims=100, max_sub_questions=12),
}


class Settings(BaseModel):
    # Services
    postgres_dsn: str = "postgresql+psycopg://research:research@localhost:5432/research"
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "researchpass"
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "research_passages"
    redis_url: str = "redis://localhost:6379/0"

    # LLM
    llm_provider: LLMProviderName = LLMProviderName.ANTHROPIC
    llm_model: str = "claude-sonnet-5"
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    oai_compat_base_url: str = "http://localhost:11434/v1"
    oai_compat_api_key: str = "not-needed"
    google_cloud_project: str | None = None
    google_cloud_location: str = "us-central1"
    # LangChain reliability wiring (0 requests/sec disables the rate limiter).
    llm_requests_per_second: float = 0.0
    llm_cache_backend: str = "memory"  # memory | redis | none
    llm_structured_retry_attempts: int = 2

    # Embeddings
    embed_provider: EmbeddingProviderName = EmbeddingProviderName.OPENAI
    embed_model: str = "text-embedding-3-small"
    embed_dim: int = 1536
    voyage_api_key: str | None = None

    # Search / connectors
    tavily_api_key: str | None = None
    github_token: str | None = None
    reddit_client_id: str | None = None
    reddit_client_secret: str | None = None
    reddit_user_agent: str = "evidence-research-agent/0.1"
    # Connector endpoints (kept in config, not hard-coded in the connectors).
    arxiv_api_url: str = "https://export.arxiv.org/api/query"
    arxiv_domain: str = "arxiv.org"
    semantic_scholar_search_url: str = (
        "https://api.semanticscholar.org/graph/v1/paper/search"
    )
    github_search_url: str = "https://api.github.com/search/repositories"
    reddit_base_url: str = "https://reddit.com"
    reddit_domain: str = "reddit.com"
    youtube_domain: str = "youtube.com"

    # Observability — Langfuse is a managed cloud service (not self-hosted).
    langfuse_host: str = "https://cloud.langfuse.com"
    langfuse_public_key: str | None = None
    langfuse_secret_key: str | None = None

    # Auth — JWT bearer tokens with user + session claims.
    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"
    jwt_expiry_minutes: int = 60
    # How LangGraph checkpoint threads are scoped for durable per-user resume.
    checkpoint_thread_scope: str = "user_session_research"

    # App
    crawler_user_agent: str = "evidence-research-agent/0.1"

    def cap_for(self, depth: ResearchDepth) -> DepthCap:
        return DEPTH_CAPS.get(depth, DEPTH_CAPS[DEFAULT_DEPTH])

    @property
    def postgres_libpq_dsn(self) -> str:
        """The DSN in libpq form (no SQLAlchemy driver suffix) for psycopg."""
        return self.postgres_dsn.replace("postgresql+psycopg://", "postgresql://")


def _load_from_env() -> Settings:
    """Read every setting from the environment via decouple into a Settings."""
    defaults = Settings()
    return Settings(
        postgres_dsn=config("POSTGRES_DSN", default=defaults.postgres_dsn),
        neo4j_uri=config("NEO4J_URI", default=defaults.neo4j_uri),
        neo4j_user=config("NEO4J_USER", default=defaults.neo4j_user),
        neo4j_password=config("NEO4J_PASSWORD", default=defaults.neo4j_password),
        qdrant_url=config("QDRANT_URL", default=defaults.qdrant_url),
        qdrant_collection=config("QDRANT_COLLECTION", default=defaults.qdrant_collection),
        redis_url=config("REDIS_URL", default=defaults.redis_url),
        llm_provider=config(
            "LLM_PROVIDER", default=defaults.llm_provider, cast=LLMProviderName
        ),
        llm_model=config("LLM_MODEL", default=defaults.llm_model),
        openai_api_key=config("OPENAI_API_KEY", default=defaults.openai_api_key),
        anthropic_api_key=config("ANTHROPIC_API_KEY", default=defaults.anthropic_api_key),
        oai_compat_base_url=config("OAI_COMPAT_BASE_URL", default=defaults.oai_compat_base_url),
        oai_compat_api_key=config("OAI_COMPAT_API_KEY", default=defaults.oai_compat_api_key),
        google_cloud_project=config("GOOGLE_CLOUD_PROJECT", default=defaults.google_cloud_project),
        google_cloud_location=config(
            "GOOGLE_CLOUD_LOCATION", default=defaults.google_cloud_location
        ),
        llm_requests_per_second=config(
            "LLM_REQUESTS_PER_SECOND", default=defaults.llm_requests_per_second, cast=float
        ),
        llm_cache_backend=config("LLM_CACHE_BACKEND", default=defaults.llm_cache_backend),
        llm_structured_retry_attempts=config(
            "LLM_STRUCTURED_RETRY_ATTEMPTS",
            default=defaults.llm_structured_retry_attempts,
            cast=int,
        ),
        embed_provider=config(
            "EMBED_PROVIDER", default=defaults.embed_provider, cast=EmbeddingProviderName
        ),
        embed_model=config("EMBED_MODEL", default=defaults.embed_model),
        embed_dim=config("EMBED_DIM", default=defaults.embed_dim, cast=int),
        voyage_api_key=config("VOYAGE_API_KEY", default=defaults.voyage_api_key),
        tavily_api_key=config("TAVILY_API_KEY", default=defaults.tavily_api_key),
        github_token=config("GITHUB_TOKEN", default=defaults.github_token),
        reddit_client_id=config("REDDIT_CLIENT_ID", default=defaults.reddit_client_id),
        reddit_client_secret=config("REDDIT_CLIENT_SECRET", default=defaults.reddit_client_secret),
        reddit_user_agent=config("REDDIT_USER_AGENT", default=defaults.reddit_user_agent),
        arxiv_api_url=config("ARXIV_API_URL", default=defaults.arxiv_api_url),
        arxiv_domain=config("ARXIV_DOMAIN", default=defaults.arxiv_domain),
        semantic_scholar_search_url=config(
            "SEMANTIC_SCHOLAR_SEARCH_URL", default=defaults.semantic_scholar_search_url
        ),
        github_search_url=config("GITHUB_SEARCH_URL", default=defaults.github_search_url),
        reddit_base_url=config("REDDIT_BASE_URL", default=defaults.reddit_base_url),
        reddit_domain=config("REDDIT_DOMAIN", default=defaults.reddit_domain),
        youtube_domain=config("YOUTUBE_DOMAIN", default=defaults.youtube_domain),
        langfuse_host=config("LANGFUSE_HOST", default=defaults.langfuse_host),
        langfuse_public_key=config("LANGFUSE_PUBLIC_KEY", default=defaults.langfuse_public_key),
        langfuse_secret_key=config("LANGFUSE_SECRET_KEY", default=defaults.langfuse_secret_key),
        jwt_secret=config("JWT_SECRET", default=defaults.jwt_secret),
        jwt_algorithm=config("JWT_ALGORITHM", default=defaults.jwt_algorithm),
        jwt_expiry_minutes=config(
            "JWT_EXPIRY_MINUTES", default=defaults.jwt_expiry_minutes, cast=int
        ),
        checkpoint_thread_scope=config(
            "CHECKPOINT_THREAD_SCOPE", default=defaults.checkpoint_thread_scope
        ),
        crawler_user_agent=config("CRAWLER_USER_AGENT", default=defaults.crawler_user_agent),
    )


@lru_cache
def get_settings() -> Settings:
    return _load_from_env()
