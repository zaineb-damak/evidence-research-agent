"""Entity & claim resolution — run before contradiction detection.

Sources restate the same fact differently ("128K context" vs "supports up to
128,000 tokens"). Without resolution the graph fragments into near-duplicate
nodes and contradiction detection misfires. Pipeline (§8):

    embed + similarity-search existing claims
        below threshold          -> keep as a new distinct claim
        above threshold          -> LLM reconciliation
                                        SAME          -> MERGE (fold evidence)
                                        CONTRADICTION -> keep separate + candidate
                                        DIFFERENT     -> keep separate

MERGE folds one claim's evidence into the other so a single canonical claim
accrues corroboration. CONTRADICTION candidates are handed to
detect_contradictions() for final adjudication.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from langchain_core.embeddings import Embeddings
from pydantic import BaseModel

from src.llm.base import StructuredLLM
from src.llm.chains import build_structured_chain
from src.llm.usage import token_usage
from src.models.schemas import Claim, Evidence
from src.prompts import RESOLUTION_PROMPT
from src.retrieval.semantic import cosine

SIMILARITY_THRESHOLD = 0.82


class Relation(StrEnum):
    SAME = "same"
    CONTRADICTION = "contradiction"
    DIFFERENT = "different"


class _Reconciliation(BaseModel):
    relation: Relation
    reason: str = ""


@dataclass
class ResolutionResult:
    claims: list[Claim]
    evidence: list[Evidence]
    contradiction_candidates: list[tuple[str, str]] = field(default_factory=list)
    merged_count: int = 0
    tokens_in: int = 0
    tokens_out: int = 0


def _reconcile(
    llm: StructuredLLM, claim_a_text: str, claim_b_text: str
) -> tuple[Relation, str, int, int]:
    chain = build_structured_chain(llm, RESOLUTION_PROMPT, _Reconciliation)
    envelope = chain.invoke({"claim_a": claim_a_text, "claim_b": claim_b_text})
    reconciliation: _Reconciliation = envelope["parsed"]
    tokens_in, tokens_out = token_usage(envelope["raw"])
    return reconciliation.relation, reconciliation.reason, tokens_in, tokens_out


def resolve_claims(
    llm: StructuredLLM,
    embeddings: Embeddings,
    claims: list[Claim],
    evidence: list[Evidence],
) -> ResolutionResult:
    """Deduplicate claims and surface contradiction candidates."""
    result = ResolutionResult(claims=[], evidence=list(evidence))
    if not claims:
        return result

    claim_vectors = embeddings.embed_documents([claim.text for claim in claims])
    canonical_claims: list[Claim] = []
    canonical_vectors: list[list[float]] = []
    evidence_by_claim: dict[str, list[Evidence]] = {}
    for evidence_item in result.evidence:
        evidence_by_claim.setdefault(evidence_item.claim_id, []).append(evidence_item)

    for claim, claim_vector in zip(claims, claim_vectors, strict=False):
        best_index, best_similarity = -1, 0.0
        for index, canonical_vector in enumerate(canonical_vectors):
            similarity = cosine(claim_vector, canonical_vector)
            if similarity > best_similarity:
                best_index, best_similarity = index, similarity

        if best_index == -1 or best_similarity < SIMILARITY_THRESHOLD:
            canonical_claims.append(claim)
            canonical_vectors.append(claim_vector)
            continue

        canonical_claim = canonical_claims[best_index]
        relation, _reason, tokens_in, tokens_out = _reconcile(
            llm, claim.text, canonical_claim.text
        )
        result.tokens_in += tokens_in
        result.tokens_out += tokens_out

        if relation == Relation.SAME:
            # Merge claim into the canonical one: repoint evidence, accrue corroboration.
            for evidence_item in evidence_by_claim.get(claim.id, []):
                evidence_item.claim_id = canonical_claim.id
                if evidence_item.id not in canonical_claim.evidence_ids:
                    canonical_claim.evidence_ids.append(evidence_item.id)
            result.merged_count += 1
        else:
            if relation == Relation.CONTRADICTION:
                result.contradiction_candidates.append((canonical_claim.id, claim.id))
            canonical_claims.append(claim)
            canonical_vectors.append(claim_vector)

    result.claims = canonical_claims
    return result
