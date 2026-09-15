"""Compose LangGraph checkpoint thread ids.

Checkpoints are keyed by a thread id. Scoping the thread by the owning user and
session (from the request's JWT) keeps each user's resumable state isolated;
`research` scope preserves the pre-auth behavior for tests and internal calls.
"""

from __future__ import annotations

THREAD_ID_SEPARATOR = ":"
SCOPE_USER_SESSION_RESEARCH = "user_session_research"
SCOPE_USER_RESEARCH = "user_research"
SCOPE_RESEARCH = "research"

ANONYMOUS = "anonymous"


def compose_thread_id(
    scope: str,
    research_id: str,
    user_id: str | None = None,
    session_id: str | None = None,
) -> str:
    user = user_id or ANONYMOUS
    session = session_id or ANONYMOUS
    if scope == SCOPE_USER_SESSION_RESEARCH:
        parts = [user, session, research_id]
    elif scope == SCOPE_USER_RESEARCH:
        parts = [user, research_id]
    else:
        parts = [research_id]
    return THREAD_ID_SEPARATOR.join(parts)
