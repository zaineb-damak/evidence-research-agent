"""Evidence Extractor: turn retrieved passages into structured claims.

The core principle: generated text is never evidence. Each extracted claim must
name the passage id that supports it and quote the supporting snippet verbatim.
Passages are fed as untrusted, delimited data (§22).
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from src.llm.base import StructuredLLM
from src.llm.chains import build_structured_chain
from src.llm.usage import token_usage
from src.models.schemas import Claim, ClaimStatus, Entity, EntityType, Evidence
from src.prompts import EXTRACTOR_PROMPT
from src.security.injection import wrap_untrusted


class _ExtractedEntity(BaseModel):
    name: str
    type: EntityType = EntityType.CONCEPT


class _ExtractedClaim(BaseModel):
    claim: str
    passage_id: str
    evidence_snippet: str
    entities: list[_ExtractedEntity] = Field(default_factory=list)


class ExtractionOutput(BaseModel):
    claims: list[_ExtractedClaim] = Field(default_factory=list)


class ExtractionResult:
    def __init__(self) -> None:
        self.claims: list[Claim] = []
        self.evidence: list[Evidence] = []
        self.entities: list[Entity] = []


def extract_claims(
    llm: StructuredLLM,
    passages: list[tuple[str, str, str]],  # (passage_id, source_id, text)
    max_claims: int,
) -> tuple[ExtractionResult, int, int]:
    if not passages:
        return ExtractionResult(), 0, 0

    source_by_passage = {pid: sid for pid, sid, _ in passages}
    blocks = [wrap_untrusted(f"passage_id={pid}", text) for pid, _sid, text in passages]
    passages_block = "\n\n".join(blocks)

    chain = build_structured_chain(llm, EXTRACTOR_PROMPT, ExtractionOutput)
    result_envelope = chain.invoke({"passages_block": passages_block})
    parsed: ExtractionOutput = result_envelope["parsed"]
    tokens_in, tokens_out = token_usage(result_envelope["raw"])

    result = ExtractionResult()
    entity_by_name: dict[str, Entity] = {}

    for ec in parsed.claims[:max_claims]:
        if ec.passage_id not in source_by_passage:
            continue  # hallucinated passage id — drop
        claim = Claim(text=ec.claim.strip(), status=ClaimStatus.UNVERIFIED)
        evidence = Evidence(
            claim_id=claim.id,
            passage_id=ec.passage_id,
            source_id=source_by_passage[ec.passage_id],
            snippet=ec.evidence_snippet.strip(),
        )
        claim.evidence_ids.append(evidence.id)

        for ent in ec.entities:
            key = ent.name.strip().lower()
            if not key:
                continue
            if key not in entity_by_name:
                entity_by_name[key] = Entity(name=ent.name.strip(), type=ent.type)
            if claim.subject_entity_id is None:
                claim.subject_entity_id = entity_by_name[key].id

        result.claims.append(claim)
        result.evidence.append(evidence)

    result.entities = list(entity_by_name.values())
    return result, tokens_in, tokens_out
