"""Cost accounting helper for pipeline nodes.

Nodes return a fresh CostMeter rather than mutating shared state, so this makes a
deep copy, records the token usage on it, and hands it back.
"""

from __future__ import annotations

from src.models.schemas import CostMeter
from src.reliability.cost import record_usage


def billed_cost(cost: CostMeter, model: str, tokens_in: int, tokens_out: int) -> CostMeter:
    updated_cost = cost.model_copy(deep=True)
    record_usage(updated_cost, model, tokens_in, tokens_out)
    return updated_cost
