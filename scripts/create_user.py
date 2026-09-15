"""Create an API user (for JWT login).

Usage:
    uv run python -m scripts.create_user <email> <password>

Writes to the Postgres user store; the password is bcrypt-hashed.
"""

from __future__ import annotations

import sys

from src.db.users import PostgresUserRepository

EXPECTED_ARG_COUNT = 3
USAGE = "usage: python -m scripts.create_user <email> <password>"


def main(argv: list[str]) -> int:
    if len(argv) != EXPECTED_ARG_COUNT:
        print(USAGE, file=sys.stderr)
        return 1
    _script, email, password = argv
    user = PostgresUserRepository().create(email=email, password=password)
    print(f"created user {user.id} <{user.email}>")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
