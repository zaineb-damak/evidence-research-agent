"""Verifier agent (§14): resolve claims, adjudicate contradictions, verify.

Runs the Phase 2 evidence-graph stages in the order they depend on each other:
resolution (merge paraphrases, surface contradiction candidates) ->
contradiction detection (finalize + pick winners) -> verification (assign each
claim a status, marking contradiction members CONFLICTING).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from langchain_core.embeddings import Embeddings

from src.evidence.contradiction import detect_contradictions
from src.evidence.resolution import resolve_claims
from src.evidence.verification import verify_claims
from src.llm.base import StructuredLLM
from src.models.schemas import ResearchState

# Called after each of the three internal phases below, with a short message
# and running counts. Optional and LangGraph-agnostic: this module never
# imports anything streaming-related itself.
VerificationProgressCallback = Callable[[str, dict[str, Any]], None]

RESOLUTION_PHASE_MESSAGE = "Resolved claim paraphrases"
CONTRADICTION_PHASE_MESSAGE = "Detected contradictions"
VERIFICATION_PHASE_MESSAGE = "Verified claim statuses"


def run_verification(
    llm: StructuredLLM,
    embeddings: Embeddings,
    state: ResearchState,
    on_progress: VerificationProgressCallback | None = None,
) -> tuple[int, int]:
    """Mutate state.claims/evidence/contradictions in place. Returns token usage."""
    tokens_in = tokens_out = 0

    resolution = resolve_claims(llm, embeddings, state.claims, state.evidence)
    state.claims = resolution.claims
    state.evidence = resolution.evidence
    tokens_in += resolution.tokens_in
    tokens_out += resolution.tokens_out
    if on_progress is not None:
        on_progress(RESOLUTION_PHASE_MESSAGE, {"claims_resolved": len(state.claims)})

    contradictions = detect_contradictions(
        resolution.contradiction_candidates, state.claims, state.evidence, state.sources
    )
    state.contradictions = contradictions
    contradicted_ids = {c.claim_a_id for c in contradictions} | {
        c.claim_b_id for c in contradictions
    }
    if on_progress is not None:
        on_progress(
            CONTRADICTION_PHASE_MESSAGE, {"contradictions_found": len(contradictions)}
        )

    t_in, t_out = verify_claims(llm, state.claims, state.evidence, contradicted_ids)
    tokens_in += t_in
    tokens_out += t_out
    if on_progress is not None:
        on_progress(VERIFICATION_PHASE_MESSAGE, {"claims_verified": len(state.claims)})
    return tokens_in, tokens_out
