"""Authentication routes: obtain a JWT with username/password, or sign up.

POST /auth/token verifies credentials against the user store and returns a signed
access token carrying the user id and a fresh session id. POST /auth/signup
creates a new account and auto-issues a token for it, same shape as login.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError

from apps.api.auth import create_access_token, new_session_id
from apps.api.dependencies import get_user_repository
from src.config import Settings, get_settings
from src.db.users import UserRepository
from src.exceptions import AuthenticationError
from src.security.passwords import verify_password

TOKEN_TYPE_BEARER = "bearer"
MIN_PASSWORD_LENGTH = 8

router = APIRouter()


class TokenRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = TOKEN_TYPE_BEARER


class SignupRequest(BaseModel):
    email: str
    password: str = Field(min_length=MIN_PASSWORD_LENGTH)


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


@router.post("/auth/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def signup(
    request: SignupRequest,
    users: UserRepository = Depends(get_user_repository),
    settings: Settings = Depends(get_settings),
) -> TokenResponse:
    if users.get_by_email(request.email) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=AuthenticationError.EMAIL_ALREADY_REGISTERED,
        )
    try:
        user = users.create(request.email, request.password)
    except IntegrityError:
        # Race between the get_by_email check above and this insert.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=AuthenticationError.EMAIL_ALREADY_REGISTERED,
        ) from None
    token = create_access_token(user.id, new_session_id(), settings)
    return TokenResponse(access_token=token)
