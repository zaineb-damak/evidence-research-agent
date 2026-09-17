"""Baseline schema.

Explicit, frozen table definitions for the schema as it existed at this
revision — this migration intentionally does NOT import `src.models.db` or use
`Base.metadata`. A baseline migration built from live ORM metadata silently
drifts every time a later commit edits an existing model in place (adding a
column to a table this revision already created, or adding a new model to the
same `Base`): `Base.metadata.create_all()` would then create that column/table
here too, and the later incremental migration that's supposed to add it
(0002's `users` table and `research_jobs.owner_*` columns, 0003's
`research_jobs.progress_detail`) would fail with a duplicate-object error.
Freezing this revision's DDL avoids that class of bug for good.

Revision ID: 0001_baseline
Revises:
Create Date: 2026-09-10
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR

revision: str = "0001_baseline"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

IDENTIFIER_LENGTH = 64
STATUS_LENGTH = 32
FTS_LANGUAGE = "english"


def upgrade() -> None:
    op.create_table(
        "research_jobs",
        sa.Column("id", sa.String(IDENTIFIER_LENGTH), primary_key=True),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("depth", sa.String(STATUS_LENGTH), nullable=False),
        sa.Column("source_types", JSONB(), nullable=False),
        sa.Column("status", sa.String(STATUS_LENGTH), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("report", sa.Text(), nullable=False),
        sa.Column("tokens_in", sa.Integer(), nullable=False),
        sa.Column("tokens_out", sa.Integer(), nullable=False),
        sa.Column("cost_usd", sa.Float(), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "research_tasks",
        sa.Column("id", sa.String(IDENTIFIER_LENGTH), primary_key=True),
        sa.Column(
            "job_id",
            sa.String(IDENTIFIER_LENGTH),
            sa.ForeignKey("research_jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("sub_question", sa.Text(), nullable=False),
        sa.Column("status", sa.String(STATUS_LENGTH), nullable=False),
        sa.Column("source_ids", JSONB(), nullable=False),
    )
    op.create_index("ix_research_tasks_job_id", "research_tasks", ["job_id"])

    op.create_table(
        "sources",
        sa.Column("id", sa.String(IDENTIFIER_LENGTH), primary_key=True),
        sa.Column(
            "job_id",
            sa.String(IDENTIFIER_LENGTH),
            sa.ForeignKey("research_jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("domain", sa.Text(), nullable=True),
        sa.Column("source_type", sa.String(STATUS_LENGTH), nullable=False),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("retrieved_at", sa.DateTime(), nullable=False),
        sa.Column("author", sa.Text(), nullable=True),
        sa.Column("language", sa.String(STATUS_LENGTH), nullable=False),
        sa.Column("quality", JSONB(), nullable=False),
    )
    op.create_index("ix_sources_job_id", "sources", ["job_id"])

    op.create_table(
        "documents",
        sa.Column("id", sa.String(IDENTIFIER_LENGTH), primary_key=True),
        sa.Column(
            "job_id",
            sa.String(IDENTIFIER_LENGTH),
            sa.ForeignKey("research_jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("source_id", sa.String(IDENTIFIER_LENGTH), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(IDENTIFIER_LENGTH), nullable=False),
    )
    op.create_index("ix_documents_job_id", "documents", ["job_id"])
    op.create_index("ix_documents_source_id", "documents", ["source_id"])
    op.create_index("ix_documents_content_hash", "documents", ["content_hash"])

    op.create_table(
        "passages",
        sa.Column("id", sa.String(IDENTIFIER_LENGTH), primary_key=True),
        sa.Column(
            "job_id",
            sa.String(IDENTIFIER_LENGTH),
            sa.ForeignKey("research_jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("document_id", sa.String(IDENTIFIER_LENGTH), nullable=False),
        sa.Column("source_id", sa.String(IDENTIFIER_LENGTH), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("qdrant_point_id", sa.String(IDENTIFIER_LENGTH), nullable=True),
        sa.Column(
            "search_vector",
            TSVECTOR(),
            sa.Computed(f"to_tsvector('{FTS_LANGUAGE}', text)", persisted=True),
            nullable=False,
        ),
    )
    op.create_index("ix_passages_job_id", "passages", ["job_id"])
    op.create_index("ix_passages_document_id", "passages", ["document_id"])
    op.create_index("ix_passages_source_id", "passages", ["source_id"])
    op.create_index(
        "ix_passages_search_vector", "passages", ["search_vector"], postgresql_using="gin"
    )

    op.create_table(
        "entities",
        sa.Column("id", sa.String(IDENTIFIER_LENGTH), primary_key=True),
        sa.Column(
            "job_id",
            sa.String(IDENTIFIER_LENGTH),
            sa.ForeignKey("research_jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("type", sa.String(STATUS_LENGTH), nullable=False),
        sa.Column("aliases", JSONB(), nullable=False),
    )
    op.create_index("ix_entities_job_id", "entities", ["job_id"])

    op.create_table(
        "claims",
        sa.Column("id", sa.String(IDENTIFIER_LENGTH), primary_key=True),
        sa.Column(
            "job_id",
            sa.String(IDENTIFIER_LENGTH),
            sa.ForeignKey("research_jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("subject_entity_id", sa.String(IDENTIFIER_LENGTH), nullable=True),
        sa.Column("status", sa.String(STATUS_LENGTH), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("confidence_breakdown", JSONB(), nullable=False),
        sa.Column("evidence_ids", JSONB(), nullable=False),
    )
    op.create_index("ix_claims_job_id", "claims", ["job_id"])

    op.create_table(
        "evidence",
        sa.Column("id", sa.String(IDENTIFIER_LENGTH), primary_key=True),
        sa.Column(
            "job_id",
            sa.String(IDENTIFIER_LENGTH),
            sa.ForeignKey("research_jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("claim_id", sa.String(IDENTIFIER_LENGTH), nullable=False),
        sa.Column("passage_id", sa.String(IDENTIFIER_LENGTH), nullable=False),
        sa.Column("source_id", sa.String(IDENTIFIER_LENGTH), nullable=False),
        sa.Column("snippet", sa.Text(), nullable=False),
        sa.Column("extraction_confidence", sa.Float(), nullable=False),
        sa.Column("similarity", sa.Float(), nullable=False),
    )
    op.create_index("ix_evidence_job_id", "evidence", ["job_id"])
    op.create_index("ix_evidence_claim_id", "evidence", ["claim_id"])

    op.create_table(
        "contradictions",
        sa.Column("id", sa.String(IDENTIFIER_LENGTH), primary_key=True),
        sa.Column(
            "job_id",
            sa.String(IDENTIFIER_LENGTH),
            sa.ForeignKey("research_jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("claim_a_id", sa.String(IDENTIFIER_LENGTH), nullable=False),
        sa.Column("claim_b_id", sa.String(IDENTIFIER_LENGTH), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("resolved_winner_id", sa.String(IDENTIFIER_LENGTH), nullable=True),
    )
    op.create_index("ix_contradictions_job_id", "contradictions", ["job_id"])


def downgrade() -> None:
    op.drop_table("contradictions")
    op.drop_table("evidence")
    op.drop_table("claims")
    op.drop_table("entities")
    op.drop_table("passages")
    op.drop_table("documents")
    op.drop_table("sources")
    op.drop_table("research_tasks")
    op.drop_table("research_jobs")
