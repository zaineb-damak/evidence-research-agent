"""User repository for JWT authentication.

`PostgresUserRepository` is the production store; `InMemoryUserRepository` is the
test double. Both satisfy the `UserRepository` protocol. A `User` is the domain
view returned to the auth layer (never exposes the password hash beyond
verification).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from src.db.base import session_scope
from src.models.db import UserRow
from src.security.passwords import hash_password


def _user_id() -> str:
    return f"user_{uuid.uuid4().hex[:12]}"


@dataclass(frozen=True)
class User:
    id: str
    email: str
    password_hash: str


@runtime_checkable
class UserRepository(Protocol):
    def get_by_email(self, email: str) -> User | None: ...

    def create(self, email: str, password: str) -> User: ...


def _to_user(row: UserRow) -> User:
    return User(id=row.id, email=row.email, password_hash=row.password_hash)


class PostgresUserRepository:
    def get_by_email(self, email: str) -> User | None:
        from sqlalchemy import select

        with session_scope() as session:
            row = session.scalars(
                select(UserRow).where(UserRow.email == email)
            ).first()
            return _to_user(row) if row is not None else None

    def create(self, email: str, password: str) -> User:
        with session_scope() as session:
            row = UserRow(
                id=_user_id(), email=email, password_hash=hash_password(password)
            )
            session.add(row)
            session.flush()
            return _to_user(row)


class InMemoryUserRepository:
    """Test double: stores users keyed by email."""

    def __init__(self) -> None:
        self._users_by_email: dict[str, User] = {}

    def get_by_email(self, email: str) -> User | None:
        return self._users_by_email.get(email)

    def create(self, email: str, password: str) -> User:
        user = User(id=_user_id(), email=email, password_hash=hash_password(password))
        self._users_by_email[email] = user
        return user
