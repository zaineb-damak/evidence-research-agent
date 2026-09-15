"""API authentication via JWT bearer tokens.

A token is issued by POST /auth/token (see apps/api/routes_auth.py) and carries
the user id (`sub`) and a per-login session id (`sid`). Every protected route
depends on `require_user`, which verifies the signature and expiry and returns
the caller's identity. Tokens are signed with a configured secret; with no
secret the service fails closed.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import timedelta

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.clock import utcnow
from src.config import Settings, get_settings
from src.exceptions import AuthenticationError

SUBJECT_CLAIM = "sub"
SESSION_CLAIM = "sid"
EXPIRY_CLAIM = "exp"
ISSUED_AT_CLAIM = "iat"

_bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class AuthContext:
    """The authenticated caller's identity, from verified token claims."""

    user_id: str
    session_id: str


def new_session_id() -> str:
    return uuid.uuid4().hex


def create_access_token(user_id: str, session_id: str, settings: Settings) -> str:
    if not settings.jwt_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=AuthenticationError.NO_JWT_SECRET,
        )
    issued_at = utcnow()
    expires_at = issued_at + timedelta(minutes=settings.jwt_expiry_minutes)
    payload = {
        SUBJECT_CLAIM: user_id,
        SESSION_CLAIM: session_id,
        ISSUED_AT_CLAIM: issued_at,
        EXPIRY_CLAIM: expires_at,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def require_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    settings: Settings = Depends(get_settings),
) -> AuthContext:
    """Authenticate a request by JWT bearer token. Returns the caller identity."""
    if not settings.jwt_secret:
        # Fail closed: with no signing secret, no token can be trusted.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=AuthenticationError.NO_JWT_SECRET,
        )
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=AuthenticationError.MISSING_TOKEN,
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.PyJWTError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=AuthenticationError.INVALID_TOKEN,
            headers={"WWW-Authenticate": "Bearer"},
        ) from error
    return AuthContext(
        user_id=payload[SUBJECT_CLAIM], session_id=payload[SESSION_CLAIM]
    )
