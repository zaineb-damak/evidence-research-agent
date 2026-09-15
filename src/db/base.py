"""SQLAlchemy engine, session factory, and declarative base.

A single engine is created per process from the configured Postgres DSN. Callers
use `session_scope()` for a transactional unit of work.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from src.config import get_settings

# SQLAlchemy expects a driver-qualified URL; settings already use
# "postgresql+psycopg://".
POOL_PRE_PING = True


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


@lru_cache
def get_engine() -> Engine:
    settings = get_settings()
    return create_engine(settings.postgres_dsn, pool_pre_ping=POOL_PRE_PING, future=True)


@lru_cache
def _get_session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), expire_on_commit=False, future=True)


def create_session() -> Session:
    return _get_session_factory()()


@contextmanager
def session_scope() -> Iterator[Session]:
    """Provide a transactional scope: commit on success, roll back on error."""
    session = create_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
