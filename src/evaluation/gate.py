"""Regression gate for CI.

Compares mean metrics from a DatasetResult against minimum thresholds and
returns the failures. Citation correctness/completeness carry the §21 targets;
the rest are conservative floors that a passing pipeline should clear.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.evaluation.metrics.citation import (
    CITATION_COMPLETENESS_TARGET,
    CITATION_CORRECTNESS_TARGET,
)
from src.evaluation.runner import DatasetResult

# Metric name -> minimum acceptable mean value.
METRIC_THRESHOLDS: dict[str, float] = {
    "citation_correctness": CITATION_CORRECTNESS_TARGET,
    "citation_completeness": CITATION_COMPLETENESS_TARGET,
    "groundedness": 0.9,
    "recall_at_10": 0.5,
    "claim_coverage": 0.5,
}


@dataclass(frozen=True)
class GateFailure:
    metric_name: str
    actual: float
    threshold: float


def evaluate_gate(result: DatasetResult) -> list[GateFailure]:
    failures: list[GateFailure] = []
    for metric_name, threshold in METRIC_THRESHOLDS.items():
        actual = result.mean(metric_name)
        if actual < threshold:
            failures.append(
                GateFailure(metric_name=metric_name, actual=actual, threshold=threshold)
            )
    return failures


def gate_passed(result: DatasetResult) -> bool:
    return not evaluate_gate(result)
