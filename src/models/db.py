"""SQLAlchemy ORM models — the system of record in Postgres.

Structured sub-objects (source quality, confidence breakdown, aliases, id lists)
are stored as JSONB columns so the schema stays readable without a column
explosion, while the queryable spine (jobs, sources, passages, claims) is fully
normalized. Passage text carries a tsvector for keyword (BM25-style) search.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Computed,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.clock import utcnow
from src.db.base import Base

FTS_LANGUAGE = "english"
IDENTIFIER_LENGTH = 64
STATUS_LENGTH = 32


EMAIL_LENGTH = 320
PASSWORD_HASH_LENGTH = 128


class UserRow(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(IDENTIFIER_LENGTH), primary_key=True)
    email: Mapped[str] = mapped_column(String(EMAIL_LENGTH), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(PASSWORD_HASH_LENGTH))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class ResearchJobRow(Base):
    __tablename__ = "research_jobs"

    id: Mapped[str] = mapped_column(String(IDENTIFIER_LENGTH), primary_key=True)
    owner_user_id: Mapped[str | None] = mapped_column(
        String(IDENTIFIER_LENGTH), nullable=True, index=True
    )
    owner_session_id: Mapped[str | None] = mapped_column(
        String(IDENTIFIER_LENGTH), nullable=True
    )
    question: Mapped[str] = mapped_column(Text)
    depth: Mapped[str] = mapped_column(String(STATUS_LENGTH))
    source_types: Mapped[list] = mapped_column(JSONB, default=list)
    status: Mapped[str] = mapped_column(String(STATUS_LENGTH))
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    report: Mapped[str] = mapped_column(Text, default="")

    tokens_in: Mapped[int] = mapped_column(Integer, default=0)
    tokens_out: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow
    )

    tasks: Mapped[list[ResearchTaskRow]] = relationship(
        cascade="all, delete-orphan", back_populates="job"
    )


class ResearchTaskRow(Base):
    __tablename__ = "research_tasks"

    id: Mapped[str] = mapped_column(String(IDENTIFIER_LENGTH), primary_key=True)
    job_id: Mapped[str] = mapped_column(
        ForeignKey("research_jobs.id", ondelete="CASCADE"), index=True
    )
    sub_question: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(STATUS_LENGTH))
    source_ids: Mapped[list] = mapped_column(JSONB, default=list)

    job: Mapped[ResearchJobRow] = relationship(back_populates="tasks")


class SourceRow(Base):
    __tablename__ = "sources"

    id: Mapped[str] = mapped_column(String(IDENTIFIER_LENGTH), primary_key=True)
    job_id: Mapped[str] = mapped_column(
        ForeignKey("research_jobs.id", ondelete="CASCADE"), index=True
    )
    url: Mapped[str] = mapped_column(Text)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    domain: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_type: Mapped[str] = mapped_column(String(STATUS_LENGTH))
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    author: Mapped[str | None] = mapped_column(Text, nullable=True)
    language: Mapped[str] = mapped_column(String(STATUS_LENGTH), default="en")
    quality: Mapped[dict] = mapped_column(JSONB, default=dict)


class DocumentRow(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(IDENTIFIER_LENGTH), primary_key=True)
    job_id: Mapped[str] = mapped_column(
        ForeignKey("research_jobs.id", ondelete="CASCADE"), index=True
    )
    source_id: Mapped[str] = mapped_column(String(IDENTIFIER_LENGTH), index=True)
    text: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(IDENTIFIER_LENGTH), index=True)


class PassageRow(Base):
    __tablename__ = "passages"

    id: Mapped[str] = mapped_column(String(IDENTIFIER_LENGTH), primary_key=True)
    job_id: Mapped[str] = mapped_column(
        ForeignKey("research_jobs.id", ondelete="CASCADE"), index=True
    )
    document_id: Mapped[str] = mapped_column(String(IDENTIFIER_LENGTH), index=True)
    source_id: Mapped[str] = mapped_column(String(IDENTIFIER_LENGTH), index=True)
    text: Mapped[str] = mapped_column(Text)
    ordinal: Mapped[int] = mapped_column(Integer, default=0)
    qdrant_point_id: Mapped[str | None] = mapped_column(
        String(IDENTIFIER_LENGTH), nullable=True
    )
    # Generated tsvector for full-text keyword search over the passage text.
    search_vector: Mapped[str] = mapped_column(
        TSVECTOR,
        Computed(f"to_tsvector('{FTS_LANGUAGE}', text)", persisted=True),
    )

    __table_args__ = (
        Index("ix_passages_search_vector", "search_vector", postgresql_using="gin"),
    )


class EntityRow(Base):
    __tablename__ = "entities"

    id: Mapped[str] = mapped_column(String(IDENTIFIER_LENGTH), primary_key=True)
    job_id: Mapped[str] = mapped_column(
        ForeignKey("research_jobs.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(Text)
    type: Mapped[str] = mapped_column(String(STATUS_LENGTH), default="concept")
    aliases: Mapped[list] = mapped_column(JSONB, default=list)


class ClaimRow(Base):
    __tablename__ = "claims"

    id: Mapped[str] = mapped_column(String(IDENTIFIER_LENGTH), primary_key=True)
    job_id: Mapped[str] = mapped_column(
        ForeignKey("research_jobs.id", ondelete="CASCADE"), index=True
    )
    text: Mapped[str] = mapped_column(Text)
    subject_entity_id: Mapped[str | None] = mapped_column(
        String(IDENTIFIER_LENGTH), nullable=True
    )
    status: Mapped[str] = mapped_column(String(STATUS_LENGTH))
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    confidence_breakdown: Mapped[dict] = mapped_column(JSONB, default=dict)
    evidence_ids: Mapped[list] = mapped_column(JSONB, default=list)


class EvidenceRow(Base):
    __tablename__ = "evidence"

    id: Mapped[str] = mapped_column(String(IDENTIFIER_LENGTH), primary_key=True)
    job_id: Mapped[str] = mapped_column(
        ForeignKey("research_jobs.id", ondelete="CASCADE"), index=True
    )
    claim_id: Mapped[str] = mapped_column(String(IDENTIFIER_LENGTH), index=True)
    passage_id: Mapped[str] = mapped_column(String(IDENTIFIER_LENGTH))
    source_id: Mapped[str] = mapped_column(String(IDENTIFIER_LENGTH))
    snippet: Mapped[str] = mapped_column(Text)
    extraction_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    similarity: Mapped[float] = mapped_column(Float, default=0.0)


class ContradictionRow(Base):
    __tablename__ = "contradictions"

    id: Mapped[str] = mapped_column(String(IDENTIFIER_LENGTH), primary_key=True)
    job_id: Mapped[str] = mapped_column(
        ForeignKey("research_jobs.id", ondelete="CASCADE"), index=True
    )
    claim_a_id: Mapped[str] = mapped_column(String(IDENTIFIER_LENGTH))
    claim_b_id: Mapped[str] = mapped_column(String(IDENTIFIER_LENGTH))
    rationale: Mapped[str] = mapped_column(Text)
    resolved_winner_id: Mapped[str | None] = mapped_column(
        String(IDENTIFIER_LENGTH), nullable=True
    )
