"""Benchmark dataset schema and loader (§20).

A benchmark case describes a research question and the ground truth used to
score a run: which sources should surface, which claims/topics must appear, and
which contradictions are known to exist.
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field

from src.models.schemas import ResearchDepth, SourceType


class ExpectedClaim(BaseModel):
    text: str
    # Substrings any of which, if present in a produced claim, count as a match.
    aliases: list[str] = Field(default_factory=list)


class KnownContradiction(BaseModel):
    subject: str
    description: str


class BenchmarkCase(BaseModel):
    case_id: str
    question: str
    depth: ResearchDepth = ResearchDepth.FAST
    source_types: list[SourceType] = Field(default_factory=list)
    expected_source_urls: list[str] = Field(default_factory=list)
    expected_claims: list[ExpectedClaim] = Field(default_factory=list)
    required_topics: list[str] = Field(default_factory=list)
    known_contradictions: list[KnownContradiction] = Field(default_factory=list)


class BenchmarkDataset(BaseModel):
    name: str
    cases: list[BenchmarkCase] = Field(default_factory=list)


def load_dataset(path: str | Path) -> BenchmarkDataset:
    raw_text = Path(path).read_text(encoding="utf-8")
    return BenchmarkDataset.model_validate(json.loads(raw_text))
