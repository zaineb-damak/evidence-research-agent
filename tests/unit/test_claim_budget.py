"""Claim budget: the run's claim cap is shared across sub-questions."""

from __future__ import annotations

import pytest

from src.workflows.budget import claim_budget_for_task


def test_cap_is_split_evenly_across_sub_questions():
    assert claim_budget_for_task(claim_cap=25, claims_so_far=0, tasks_remaining=5) == 5


def test_unused_budget_carries_forward_to_later_sub_questions():
    # The first sub-question only yielded 1 of its 5; the other 4 share the rest.
    assert claim_budget_for_task(claim_cap=25, claims_so_far=1, tasks_remaining=4) == 6


def test_no_budget_once_cap_is_reached():
    assert claim_budget_for_task(claim_cap=25, claims_so_far=25, tasks_remaining=2) == 0


@pytest.mark.parametrize("claim_cap, task_count", [(25, 5), (25, 8), (50, 8), (100, 12), (3, 5)])
def test_greedy_sub_questions_never_exceed_the_cap_and_each_gets_a_turn(claim_cap, task_count):
    claims_so_far = 0
    budgets = []
    for tasks_remaining in range(task_count, 0, -1):
        budget = claim_budget_for_task(claim_cap, claims_so_far, tasks_remaining)
        budgets.append(budget)
        claims_so_far += budget  # every sub-question uses its whole budget
    assert claims_so_far == min(claim_cap, claims_so_far)
    assert claims_so_far == claim_cap
    if claim_cap >= task_count:
        assert all(budget >= 1 for budget in budgets)
