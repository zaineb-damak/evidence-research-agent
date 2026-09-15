"""Alembic environment.

Pulls the database URL from application settings and exposes the ORM metadata as
the autogenerate target, so `alembic revision --autogenerate` compares against
the models in src/models/db.py.
"""

from __future__ import annotations

from alembic import context
from sqlalchemy import engine_from_config, pool

# Import the models module so every table is registered on Base.metadata.
import src.models.db  # noqa: F401
from src.config import get_settings
from src.db.base import Base

config = context.config
config.set_main_option("sqlalchemy.url", get_settings().postgres_dsn)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
