"""Generation-quality metrics against a benchmark case.

- topic_completeness: fraction of required topics mentioned in the report.
- groundedness: fraction of claims backed by at least one piece of evidence.
- claim_coverage: fraction of expected claims matched by a produced claim.
"""

from __future__ import annotations

from src.evaluation.dataset import ExpectedClaim
from src.models.schemas import Claim

PERFECT_SCORE = 1.0


def _text_contains_any(haystack: str, needles: list[str]) -> bool:
    lowered = haystack.lower()
    return any(needle.lower() in lowered for needle in needles if needle)


def topic_completeness(report_text: str, required_topics: list[str]) -> float:
    if not required_topics:
        return PERFECT_SCORE
    lowered_report = report_text.lower()
    covered = sum(1 for topic in required_topics if topic.lower() in lowered_report)
    return covered / len(required_topics)


def groundedness(claims: list[Claim]) -> float:
    if not claims:
        return PERFECT_SCORE
    grounded = sum(1 for claim in claims if claim.evidence_ids)
    return grounded / len(claims)


def claim_coverage(
    produced_claims: list[Claim], expected_claims: list[ExpectedClaim]
) -> float:
    if not expected_claims:
        return PERFECT_SCORE
    produced_texts = [claim.text for claim in produced_claims]
    matched = 0
    for expected in expected_claims:
        match_targets = [expected.text, *expected.aliases]
        if any(_text_contains_any(text, match_targets) for text in produced_texts):
            matched += 1
    return matched / len(expected_claims)
