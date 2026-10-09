"""The summary prompt must not tell the model that unverified claims are verified.

Regression: every reportable claim was listed under "Verified claims", so a run
with no VERIFIED claim still produced a summary that said "the verified claims
indicate...". The summary is the most-read part of the report; it has to carry
each claim's real status.
"""

from __future__ import annotations

from src.models.schemas import ClaimStatus
from src.prompts import SYNTHESIZER_SUMMARY_PROMPT

CLAIM_LINES = "- Postgres FTS suits small apps. [partially_supported]"


def _rendered_prompt() -> str:
    messages = SYNTHESIZER_SUMMARY_PROMPT.format_messages(
        question="Is Postgres FTS enough?", claim_lines=CLAIM_LINES
    )
    return "\n".join(str(message.content) for message in messages)


def test_claims_are_not_labelled_verified_wholesale():
    assert "Verified claims" not in _rendered_prompt()
    assert "verified claims listed" not in _rendered_prompt()


def test_prompt_explains_every_status_the_claims_can_carry():
    prompt = _rendered_prompt()
    for status in (ClaimStatus.VERIFIED, ClaimStatus.PARTIALLY_SUPPORTED, ClaimStatus.CONFLICTING):
        assert status.value in prompt
