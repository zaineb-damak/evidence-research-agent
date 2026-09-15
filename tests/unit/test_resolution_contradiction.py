"""Phase 2: entity/claim resolution, contradiction detection, verification."""

from __future__ import annotations

from src.evidence.contradiction import detect_contradictions
from src.evidence.resolution import resolve_claims
from src.evidence.verification import verify_claims
from src.models.schemas import (
    Claim,
    ClaimStatus,
    Evidence,
    Source,
    SourceQuality,
    SourceType,
)
from tests.conftest import TableEmbeddings, fixed_response, structured_llm


def _claim(text: str) -> tuple[Claim, Evidence]:
    c = Claim(text=text)
    e = Evidence(claim_id=c.id, passage_id="p", source_id="s", snippet=text)
    c.evidence_ids.append(e.id)
    return c, e


def test_resolution_merges_paraphrases():
    a, ea = _claim("Model X supports 128K context.")
    b, eb = _claim("Model X supports up to 128,000 tokens.")
    embedder = TableEmbeddings({a.text: [1.0, 0.0, 0.0], b.text: [1.0, 0.0, 0.0]})
    llm = structured_llm(fixed_response({"relation": "same"}))

    res = resolve_claims(llm, embedder, [a, b], [ea, eb])

    assert len(res.claims) == 1
    assert res.merged_count == 1
    # Both pieces of evidence now point at the surviving canonical claim.
    survivor = res.claims[0]
    assert set(survivor.evidence_ids) == {ea.id, eb.id}
    assert not res.contradiction_candidates


def test_resolution_flags_contradiction_candidate():
    a, ea = _claim("Model X supports 128K context.")
    b, eb = _claim("Model X supports 32K context.")
    embedder = TableEmbeddings({a.text: [1.0, 0.0, 0.0], b.text: [1.0, 0.0, 0.0]})
    llm = structured_llm(fixed_response({"relation": "contradiction"}))

    res = resolve_claims(llm, embedder, [a, b], [ea, eb])

    assert len(res.claims) == 2  # kept separate
    assert res.contradiction_candidates == [(a.id, b.id)]


def test_resolution_keeps_dissimilar_claims_without_llm():
    a, ea = _claim("Model X supports 128K context.")
    b, eb = _claim("Model Y is released under Apache 2.0.")
    # Orthogonal vectors -> below threshold -> no reconciliation call.
    embedder = TableEmbeddings({a.text: [1.0, 0.0, 0.0], b.text: [0.0, 1.0, 0.0]})
    llm = structured_llm(fixed_response({"relation": "contradiction"}))  # must NOT be consulted

    res = resolve_claims(llm, embedder, [a, b], [ea, eb])

    assert len(res.claims) == 2
    assert not res.contradiction_candidates


def test_contradiction_picks_higher_quality_winner():
    a, ea = _claim("Model X supports 128K context.")
    b, eb = _claim("Model X supports 32K context.")
    ea.source_id, eb.source_id = "doc", "blog"
    doc = Source(id="doc", url="u1", source_type=SourceType.DOCUMENTATION,
                 quality=SourceQuality(score=0.9))
    blog = Source(id="blog", url="u2", source_type=SourceType.WEB,
                  quality=SourceQuality(score=0.3))

    contras = detect_contradictions([(a.id, b.id)], [a, b], [ea, eb], [doc, blog])

    assert len(contras) == 1
    assert contras[0].resolved_winner_id == a.id  # documentation wins over blog


def test_verifier_marks_conflicting_and_unsupported():
    conflicting, ce = _claim("Model X supports 128K context.")
    ce.similarity = 0.9
    conflicting.confidence = 0.5
    orphan = Claim(text="Unsupported floating claim.")  # no evidence

    llm = structured_llm(fixed_response({"entailment": "entailed"}))
    verify_claims(llm, [conflicting, orphan], [ce], contradicted_ids={conflicting.id})

    assert conflicting.status == ClaimStatus.CONFLICTING
    assert orphan.status == ClaimStatus.UNSUPPORTED


def test_verifier_marks_verified_on_entailment():
    c, e = _claim("Model X supports 128K context.")
    e.similarity = 0.9
    c.confidence = 0.5
    llm = structured_llm(fixed_response({"entailment": "entailed"}))

    verify_claims(llm, [c], [e], contradicted_ids=set())
    assert c.status == ClaimStatus.VERIFIED
