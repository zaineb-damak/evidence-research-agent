"""Password hashing via bcrypt.

Kept in one place so the hashing scheme is defined once and both the user-creation
path and the login path use the same verifier. bcrypt ignores bytes past 72, so
inputs are pre-hashed with SHA-256 to remove that ceiling while staying a single
bcrypt verification.
"""

from __future__ import annotations

import base64
import hashlib

import bcrypt

ENCODING = "utf-8"


def _prehash(plaintext: str) -> bytes:
    # SHA-256 then base64 keeps the bcrypt input <= 72 bytes for any password.
    digest = hashlib.sha256(plaintext.encode(ENCODING)).digest()
    return base64.b64encode(digest)


def hash_password(plaintext: str) -> str:
    return bcrypt.hashpw(_prehash(plaintext), bcrypt.gensalt()).decode(ENCODING)


def verify_password(plaintext: str, password_hash: str) -> bool:
    return bcrypt.checkpw(_prehash(plaintext), password_hash.encode(ENCODING))
