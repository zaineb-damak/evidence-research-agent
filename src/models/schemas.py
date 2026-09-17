"""Pydantic domain schemas shared across the pipeline and API.

These are the in-memory transfer objects. Persistence models (SQLAlchemy) live
in src/models/db.py and are kept deliberately close to these shapes.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from src.clock import utcnow


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


class ResearchDepth(StrEnum):
    FAST = "fast"
    NORMAL = "normal"
    DEEP = "deep"


class SourceType(StrEnum):
    WEB = "web"
    PAPER = "paper"
    DOCUMENTATION = "documentation"
    GITHUB = "github"
    ARXIV = "arxiv"
    YOUTUBE = "youtube"
    REDDIT = "reddit"
    API = "api"


class ResearchStatus(StrEnum):
    QUEUED = "queued"
    PLANNING = "planning"
    SEARCHING = "searching"
    EXTRACTING = "extracting"
    RESOLVING = "resolving"
    VERIFYING = "verifying"
    SYNTHESIZING = "synthesizing"
    COMPLETED = "completed"
    FAILED = "failed"


class ClaimStatus(StrEnum):
    VERIFIED = "verified"
    PARTIALLY_SUPPORTED = "partially_supported"
    CONFLICTING = "conflicting"
    UNSUPPORTED = "unsupported"
    UNVERIFIED = "unverified"  # not yet run through the verifier


class EntityType(StrEnum):
    """Kind of entity a claim concerns. CONCEPT is the safe default."""

    CONCEPT = "concept"
    PERSON = "person"
    ORGANIZATION = "organization"
    LOCATION = "location"
    TECHNOLOGY = "technology"
    MODEL = "model"
    METRIC = "metric"


class GraphLabel(StrEnum):
    """Node labels in the Neo4j evidence graph. Single source of truth shared by
    the projection (src/evidence/graph.py) and the store (src/stores/graph.py)."""

    SOURCE = "Source"
    DOCUMENT = "Document"
    PASSAGE = "Passage"
    CLAIM = "Claim"
    ENTITY = "Entity"


class GraphRelation(StrEnum):
    """Relationship verbs in the evidence graph (§8). Single source of truth."""

    CONTAINS = "CONTAINS"
    SUPPORTS = "SUPPORTS"
    CONTRADICTS = "CONTRADICTS"
    ABOUT = "ABOUT"
    DERIVED_FROM = "DERIVED_FROM"
    RELATED_TO = "RELATED_TO"
    ANSWERS = "ANSWERS"
    CITES = "CITES"


class WorkflowRoute(StrEnum):
    """Conditional-edge outcomes after the search node in the LangGraph pipeline."""

    HAS_PASSAGES = "has_passages"
    NO_PASSAGES = "no_passages"


class NodeName(StrEnum):
    """LangGraph node identifiers for the research pipeline graph.

    Lives here (rather than in src/workflows/nodes.py, which defines the node
    functions) so both src/workflows/nodes.py and src/workflows/progress_emitter.py
    can import it without a circular dependency between those two modules.
    """

    PLAN = "plan"
    SEARCH = "search"
    EXTRACT = "extract"
    SCORE = "score"
    VERIFY = "verify"
    SYNTHESIZE = "synthesize"


# --- Source acquisition ---------------------------------------------------


class SourceQuality(BaseModel):
    """§6 breakdown. Each term is measurable; total is normalized 0..1."""

    authority: float = 0.0
    recency: float = 0.0
    relevance: float = 0.0
    primary_source_bonus: float = 0.0
    corroboration: float = 0.0
    score: float = 0.0


class Source(BaseModel):
    id: str = Field(default_factory=lambda: _id("source"))
    url: str
    title: str | None = None
    domain: str | None = None
    source_type: SourceType = SourceType.WEB
    published_at: datetime | None = None
    retrieved_at: datetime = Field(default_factory=utcnow)
    author: str | None = None
    language: str = "en"
    quality: SourceQuality = Field(default_factory=SourceQuality)


class Document(BaseModel):
    id: str = Field(default_factory=lambda: _id("doc"))
    source_id: str
    text: str
    content_hash: str


class Passage(BaseModel):
    id: str = Field(default_factory=lambda: _id("passage"))
    document_id: str
    source_id: str
    text: str
    ordinal: int
    qdrant_point_id: str | None = None


# --- Evidence graph -------------------------------------------------------


class Entity(BaseModel):
    id: str = Field(default_factory=lambda: _id("entity"))
    name: str
    type: EntityType = EntityType.CONCEPT
    aliases: list[str] = Field(default_factory=list)


class Evidence(BaseModel):
    """Passage-level support for a claim. Never generated text."""

    id: str = Field(default_factory=lambda: _id("evidence"))
    claim_id: str
    passage_id: str
    source_id: str
    snippet: str
    extraction_confidence: float = 0.0
    similarity: float = 0.0


class ConfidenceBreakdown(BaseModel):
    source_quality: float = 0.0
    evidence_strength: float = 0.0
    source_agreement: float = 0.0
    extraction_confidence: float = 0.0
    total: float = 0.0


class Claim(BaseModel):
    id: str = Field(default_factory=lambda: _id("claim"))
    text: str
    subject_entity_id: str | None = None
    status: ClaimStatus = ClaimStatus.UNVERIFIED
    confidence: float = 0.0
    confidence_breakdown: ConfidenceBreakdown = Field(default_factory=ConfidenceBreakdown)
    evidence_ids: list[str] = Field(default_factory=list)


class Contradiction(BaseModel):
    id: str = Field(default_factory=lambda: _id("contra"))
    claim_a_id: str
    claim_b_id: str
    rationale: str
    resolved_winner_id: str | None = None


# --- Planning / orchestration --------------------------------------------


class ResearchTask(BaseModel):
    id: str = Field(default_factory=lambda: _id("task"))
    sub_question: str
    status: ResearchStatus = ResearchStatus.QUEUED
    source_ids: list[str] = Field(default_factory=list)


class ResearchRequest(BaseModel):
    question: str
    depth: ResearchDepth = ResearchDepth.FAST
    source_types: list[SourceType] = Field(
        default_factory=lambda: [SourceType.WEB, SourceType.PAPER, SourceType.DOCUMENTATION]
    )


class ResearchJobListItem(BaseModel):
    """Lightweight per-job projection for the session-history list
    (`GET /api/research`). Named distinctly from the single-job detail shape
    returned by `GET /api/research/{id}` to avoid confusing the two response
    shapes on either side of the API.
    """

    research_id: str
    question: str
    status: ResearchStatus
    depth: ResearchDepth
    error: str | None = None
    created_at: datetime
    updated_at: datetime


class CostMeter(BaseModel):
    tokens_in: int = 0
    tokens_out: int = 0
    usd: float = 0.0
    latency_ms: int = 0


class ResearchState(BaseModel):
    """Explicit, serializable job state (§15). LangGraph passes this between nodes."""

    research_id: str = Field(default_factory=lambda: _id("res"))
    original_question: str
    depth: ResearchDepth = ResearchDepth.FAST
    source_types: list[SourceType] = Field(default_factory=list)

    # Ownership (from the caller's JWT). Scopes checkpoint threads and access.
    owner_user_id: str | None = None
    owner_session_id: str | None = None

    research_tasks: list[ResearchTask] = Field(default_factory=list)
    sources: list[Source] = Field(default_factory=list)
    documents: list[Document] = Field(default_factory=list)
    passages: list[Passage] = Field(default_factory=list)
    entities: list[Entity] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    claims: list[Claim] = Field(default_factory=list)
    contradictions: list[Contradiction] = Field(default_factory=list)

    report: str = ""
    status: ResearchStatus = ResearchStatus.QUEUED
    error: str | None = None
    cost: CostMeter = Field(default_factory=CostMeter)

    # Transient passage embeddings, threaded between the extract and score graph
    # nodes. Excluded from API serialization (large and internal); the graph
    # checkpointer still persists it so a resumed run need not re-embed.
    passage_vectors: dict[str, list[float]] = Field(default_factory=dict, exclude=True)
