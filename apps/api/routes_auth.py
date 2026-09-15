"""Authentication routes: obtain a JWT with username/password.

POST /auth/token verifies credentials against the user store and returns a signed
access token carrying the user id and a fresh session id.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from apps.api.auth import create_access_token, new_session_id
from apps.api.dependencies import get_user_repository
from src.config import Settings, get_settings
from src.db.users import UserRepository
from src.exceptions import AuthenticationError
from src.security.passwords import verify_password

TOKEN_TYPE_BEARER = "bearer"

router = APIRouter()


class TokenRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = TOKEN_TYPE_BEARER


@router.post("/auth/token", response_model=TokenResponse)
def issue_token(
    credentials: TokenRequest,
    users: UserRepository = Depends(get_user_repository),
    settings: Settings = Depends(get_settings),
) -> TokenResponse:
    user = users.get_by_email(credentials.email)
    if user is None or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=AuthenticationError.INVALID_CREDENTIALS,
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(user.id, new_session_id(), settings)
    return TokenResponse(access_token=token)
