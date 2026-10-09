"""Share a run's claim cap across its planned sub-questions.

Handing each sub-question the whole cap let the first one fill it, so the
remaining sub-questions were never extracted and the report covered one
angle of the question. Each sub-question instead gets an even share of what
is left, so budget a sub-question doesn't use carries forward and the total
never exceeds the cap.
"""

from __future__ import annotations

import math

NO_BUDGET = 0


def claim_budget_for_task(claim_cap: int, claims_so_far: int, tasks_remaining: int) -> int:
    remaining_claims = claim_cap - claims_so_far
    if remaining_claims <= NO_BUDGET or tasks_remaining <= NO_BUDGET:
        return NO_BUDGET
    return math.ceil(remaining_claims / tasks_remaining)
