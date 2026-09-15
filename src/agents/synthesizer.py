"""Synthesizer: organize verified claims into the §12 report structure.

Findings are rendered directly from claims with per-claim citation markers and
confidence bars, so every important statement is traceable. The LLM writes only
the executive summary, constrained to the verified claim list (it may not
introduce new facts). Pure formatting lives in src/evidence/report_format.py.
"""

from __future__ import annotations

from collections import Counter

from pydantic import BaseModel

from src.evidence.citations import CitationIndex
from src.evidence.report_format import confidence_bar, format_markers, render_conflicts
from src.llm.base import StructuredLLM
from src.llm.chains import build_structured_chain
from src.llm.usage import token_usage
from src.models.schemas import Claim, ClaimStatus, ResearchState
from src.prompts import SYNTHESIZER_SUMMARY_PROMPT

NO_FINDINGS_SUMMARY = "No supported findings were produced."
SUMMARY_UNAVAILABLE = "Summary unavailable; see findings below."


class _Summary(BaseModel):
    executive_summary: str


def generate_executive_summary(
    llm: StructuredLLM, question: str, claims: list[Claim]
) -> tuple[str, int, int]:
    if not claims:
        return NO_FINDINGS_SUMMARY, 0, 0
    claim_lines = "\n".join(f"- {claim.text} [{claim.status}]" for claim in claims)
    chain = build_structured_chain(llm, SYNTHESIZER_SUMMARY_PROMPT, _Summary)
    try:
        envelope = chain.invoke({"question": question, "claim_lines": claim_lines})
    except Exception:
        return SUMMARY_UNAVAILABLE, 0, 0
    summary: _Summary = envelope["parsed"]
    tokens_in, tokens_out = token_usage(envelope["raw"])
    return summary.executive_summary.strip(), tokens_in, tokens_out


def synthesize_report(llm: StructuredLLM, state: ResearchState) -> tuple[str, int, int]:
    claims = state.claims
    evidence = state.evidence
    sources = state.sources
    reportable = [claim for claim in claims if claim.status != ClaimStatus.UNSUPPORTED]

    citations = CitationIndex()
    summary, tokens_in, tokens_out = generate_executive_summary(
        llm, state.original_question, reportable
    )

    parts: list[str] = ["# Research Report", "", "## Executive Summary", "", summary, ""]
    parts += ["## Research Question", "", state.original_question, ""]

    # Methodology
    sources_by_type = Counter(source.source_type for source in sources)
    parts += ["## Methodology", "", "Sources:"]
    parts += [f"- {count} × {source_type}" for source_type, count in sources_by_type.items()]
    parts += [f"- {len(state.passages)} passages, {len(claims)} claims extracted", ""]

    # Findings
    parts += ["## Findings", ""]
    for claim in reportable:
        markers = citations.markers_for_claim(claim, evidence)
        cite_str = f" {format_markers(markers)}" if markers else ""
        parts.append(f"- {claim.text}{cite_str}")
        parts.append(f"  - {claim.status.upper()} — {confidence_bar(claim.confidence)}")
    parts.append("")

    # Conflicting evidence
    parts += render_conflicts(state.contradictions, claims, citations, evidence)

    # Limitations
    unsupported = [claim for claim in claims if claim.status == ClaimStatus.UNSUPPORTED]
    parts += ["## Limitations", ""]
    if unsupported:
        parts.append(
            f"{len(unsupported)} extracted claim(s) lacked sufficient evidence "
            "and were excluded from the findings."
        )
    else:
        parts.append("No important claims were left unsupported.")
    parts.append("")

    # Sources (must come after all cite() calls above)
    parts += ["## Sources", "", citations.render_sources(sources), ""]

    return "\n".join(parts), tokens_in, tokens_out
