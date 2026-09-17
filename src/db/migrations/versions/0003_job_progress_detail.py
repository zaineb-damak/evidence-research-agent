"""Add research_jobs.progress_detail for live-progress reconnect snapshots.

The pipeline *stage* a job is in is already covered by the existing `status`
column (one ResearchStatus member per stage); this adds a nullable JSONB
column to also persist the current stage's sub-step detail (e.g. running
sources/claims counts), so a client connecting to the SSE endpoint
(GET /api/research/{id}/events) mid-run gets a useful first SNAPSHOT event
instead of an empty one.

Revision ID: 0003_job_progress_detail
Revises: 0002_users_and_job_owner
Create Date: 2026-09-16
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0003_job_progress_detail"
down_revision: str | None = "0002_users_and_job_owner"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "research_jobs",
        sa.Column("progress_detail", JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("research_jobs", "progress_detail")
