"""Users table and job ownership columns.

Adds the `users` table (JWT authentication) and nullable owner columns on
`research_jobs`. Owner columns are nullable so pre-existing jobs remain valid
(they read back as unowned and are accessible to any authenticated caller).

Revision ID: 0002_users_and_job_owner
Revises: 0001_baseline
Create Date: 2026-09-15
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from src.models.db import (
    EMAIL_LENGTH,
    IDENTIFIER_LENGTH,
    PASSWORD_HASH_LENGTH,
)

revision: str = "0002_users_and_job_owner"
down_revision: str | None = "0001_baseline"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(IDENTIFIER_LENGTH), primary_key=True),
        sa.Column("email", sa.String(EMAIL_LENGTH), nullable=False),
        sa.Column("password_hash", sa.String(PASSWORD_HASH_LENGTH), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.add_column(
        "research_jobs",
        sa.Column("owner_user_id", sa.String(IDENTIFIER_LENGTH), nullable=True),
    )
    op.add_column(
        "research_jobs",
        sa.Column("owner_session_id", sa.String(IDENTIFIER_LENGTH), nullable=True),
    )
    op.create_index(
        "ix_research_jobs_owner_user_id", "research_jobs", ["owner_user_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_research_jobs_owner_user_id", table_name="research_jobs")
    op.drop_column("research_jobs", "owner_session_id")
    op.drop_column("research_jobs", "owner_user_id")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
