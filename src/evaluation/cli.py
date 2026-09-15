"""Command-line entry point to run a benchmark dataset and enforce the gate.

Usage:
    python -m src.evaluation.cli evals/datasets/example.json

Exits non-zero if the regression gate fails, so CI blocks on quality drops.
Live provider/connector dependencies are built from settings.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from src.evaluation.dataset import load_dataset
from src.evaluation.gate import evaluate_gate
from src.evaluation.runner import DatasetResult, run_dataset
from src.workflows.deps import build_deps

EXIT_SUCCESS = 0
EXIT_GATE_FAILED = 1
REPORTS_DIRECTORY = Path("evals/reports")


def _write_report(result: DatasetResult) -> Path:
    REPORTS_DIRECTORY.mkdir(parents=True, exist_ok=True)
    report_path = REPORTS_DIRECTORY / f"{result.dataset_name}.json"
    report_path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
    return report_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run an evidence-agent benchmark.")
    parser.add_argument("dataset_path", help="Path to a benchmark dataset JSON file.")
    arguments = parser.parse_args(argv)

    dataset = load_dataset(arguments.dataset_path)
    # Source types are taken per-case; seed deps from the first case's selection.
    seed_source_types = dataset.cases[0].source_types if dataset.cases else []
    deps = build_deps(seed_source_types)

    result = run_dataset(dataset, deps)
    report_path = _write_report(result)

    failures = evaluate_gate(result)
    summary = {
        "dataset": result.dataset_name,
        "cases": len(result.case_results),
        "report": str(report_path),
        "failures": [failure.__dict__ for failure in failures],
    }
    print(json.dumps(summary, indent=2))

    return EXIT_GATE_FAILED if failures else EXIT_SUCCESS


if __name__ == "__main__":
    sys.exit(main())
