"""Claim verification (§10).

Each claim is classified into VERIFIED / PARTIALLY_SUPPORTED / CONFLICTING /
UNSUPPORTED by combining three signals:
- an LLM entailment check (does the supporting snippet actually entail the claim?),
- the measurable confidence already computed, and
- membership in a detected contradiction.

The LLM is used only for the entailment judgment (an alignment task), never to
invent a confidence number.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel

from src.llm.base import StructuredLLM
from src.llm.chains import build_structured_chain
from src.llm.usage import token_usage
from src.models.schemas import Claim, ClaimStatus, Evidence
from src.prompts import VERIFICATION_PROMPT
from src.security.injection import wrap_untrusted

ENTAILED_MIN_CONFIDENCE = 0.15
PARTIAL_MIN_CONFIDENCE = 0.05


class Entailment(StrEnum):
    ENTAILED = "entailed"
    PARTIAL = "partial"
    NOT_ENTAILED = "not_entailed"


class _EntailmentJudgment(BaseModel):
    entailment: Entailment


def _entail(llm: StructuredLLM, claim: str, snippet: str) -> tuple[Entailment, int, int]:
    chain = build_structured_chain(llm, VERIFICATION_PROMPT, _EntailmentJudgment)
    envelope = chain.invoke(
        {"claim": claim, "evidence_block": wrap_untrusted("evidence", snippet)}
    )
    judgment: _EntailmentJudgment = envelope["parsed"]
    tokens_in, tokens_out = token_usage(envelope["raw"])
    return judgment.entailment, tokens_in, tokens_out


def verify_claims(
    llm: StructuredLLM,
    claims: list[Claim],
    evidence: list[Evidence],
    contradicted_ids: set[str],
) -> tuple[int, int]:
    """Assign a status to each claim in place. Returns token usage."""
    ev_by_id = {e.id: e for e in evidence}
    tokens_in = tokens_out = 0

    for claim in claims:
        claim_ev = [ev_by_id[eid] for eid in claim.evidence_ids if eid in ev_by_id]
        if not claim_ev:
            claim.status = ClaimStatus.UNSUPPORTED
            continue

        if claim.id in contradicted_ids:
            claim.status = ClaimStatus.CONFLICTING
            continue

        best = max(claim_ev, key=lambda e: e.similarity)
        entailment, t_in, t_out = _entail(llm, claim.text, best.snippet)
        tokens_in += t_in
        tokens_out += t_out

        if entailment == Entailment.NOT_ENTAILED:
            claim.status = ClaimStatus.UNSUPPORTED
        elif entailment == Entailment.ENTAILED and claim.confidence >= ENTAILED_MIN_CONFIDENCE:
            claim.status = ClaimStatus.VERIFIED
        elif claim.confidence >= PARTIAL_MIN_CONFIDENCE:
            claim.status = ClaimStatus.PARTIALLY_SUPPORTED
        else:
            claim.status = ClaimStatus.UNSUPPORTED

    return tokens_in, tokens_out
