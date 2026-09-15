"""Token cost accounting.

Turns token usage into a running USD estimate so cost is surfaced in job status,
not just logged. Prices are per-million-tokens and configurable; unknown models
fall back to a conservative default rather than reporting zero.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.models.schemas import CostMeter

TOKENS_PER_MILLION = 1_000_000


@dataclass(frozen=True)
class ModelPrice:
    input_usd_per_million_tokens: float
    output_usd_per_million_tokens: float


# Indicative public list prices (USD per million tokens). Update as needed;
# the point is a measurable cost signal, not billing-grade accounting.
MODEL_PRICES: dict[str, ModelPrice] = {
    "claude-sonnet-5": ModelPrice(3.0, 15.0),
    "claude-opus-5": ModelPrice(15.0, 75.0),
    "claude-haiku-4-5-20251001": ModelPrice(1.0, 5.0),
    "gpt-4o": ModelPrice(2.5, 10.0),
    "gpt-4o-mini": ModelPrice(0.15, 0.6),
}

DEFAULT_MODEL_PRICE = ModelPrice(
    input_usd_per_million_tokens=3.0,
    output_usd_per_million_tokens=15.0,
)


def price_for_model(model: str) -> ModelPrice:
    return MODEL_PRICES.get(model, DEFAULT_MODEL_PRICE)


def estimate_cost_usd(model: str, tokens_in: int, tokens_out: int) -> float:
    price = price_for_model(model)
    input_cost = tokens_in / TOKENS_PER_MILLION * price.input_usd_per_million_tokens
    output_cost = tokens_out / TOKENS_PER_MILLION * price.output_usd_per_million_tokens
    return input_cost + output_cost


def record_usage(cost_meter: CostMeter, model: str, tokens_in: int, tokens_out: int) -> None:
    """Add token usage and its USD estimate to a running cost meter, in place."""
    cost_meter.tokens_in += tokens_in
    cost_meter.tokens_out += tokens_out
    cost_meter.usd += estimate_cost_usd(model, tokens_in, tokens_out)
