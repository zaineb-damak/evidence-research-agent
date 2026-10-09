"""Extraction covers every planned sub-question, not just the first.

Regression: each sub-question used to receive the whole run's claim cap, so a
prolific first sub-question filled the cap and the rest were never extracted.
"""

from __future__ import annotations

from src.config import get_settings
from src.models.progress import ProgressEventType
from src.models.schemas import NodeName, ResearchDepth, ResearchState, ResearchStatus
from src.workflows.research import run_pipeline
from tests.conftest import _first_passage_id, make_deps, pipeline_response, structured_llm

SUB_QUESTIONS = [f"Sub-question {number} about Model X?" for number in range(1, 6)]
CLAIMS_PER_EXTRACTION_REPLY = 40  # more than the whole FAST cap


def _prolific_responder(extraction_prompts: list[str]):
    def respond(prompt_text: str) -> dict:
        if "research planner" in prompt_text:
            return {"sub_questions": SUB_QUESTIONS}
        if "extract factual claims" in prompt_text:
            extraction_prompts.append(prompt_text)
            call_number = len(extraction_prompts)
            return {
                "claims": [
                    {
                        "claim": f"Claim {index} from extraction {call_number}.",
                        "passage_id": _first_passage_id(prompt_text),
                        "evidence_snippet": "Model X supports a context length of 128K tokens.",
                        "entities": [],
                    }
                    for index in range(CLAIMS_PER_EXTRACTION_REPLY)
                ]
            }
        return pipeline_response(prompt_text)

    return respond


def test_every_sub_question_is_extracted_within_the_claim_cap(fake_embedder, fake_connectors):
    extraction_prompts: list[str] = []
    llm = structured_llm(_prolific_responder(extraction_prompts))
    deps, _index, _graph = make_deps(llm, fake_embedder, fake_connectors)
    state = ResearchState(original_question="Tell me about Model X", depth=ResearchDepth.FAST)
    events = []

    result = run_pipeline(state, deps, on_progress_event=events.append)

    assert result.status == ResearchStatus.COMPLETED
    assert len(extraction_prompts) == len(SUB_QUESTIONS)
    extract_completed = next(
        event
        for event in events
        if event.event_type == ProgressEventType.STAGE_COMPLETED
        and event.stage == NodeName.EXTRACT.value
    )
    claim_cap = get_settings().cap_for(ResearchDepth.FAST).max_claims
    assert extract_completed.detail["claims_count"] <= claim_cap
    assert extract_completed.detail["evidence_count"] == extract_completed.detail["claims_count"]


def test_extraction_prompt_states_the_sub_question_budget(fake_embedder, fake_connectors):
    extraction_prompts: list[str] = []
    llm = structured_llm(_prolific_responder(extraction_prompts))
    deps, _index, _graph = make_deps(llm, fake_embedder, fake_connectors)

    run_pipeline(ResearchState(original_question="Model X", depth=ResearchDepth.FAST), deps)

    claim_cap = get_settings().cap_for(ResearchDepth.FAST).max_claims
    first_budget = claim_cap // len(SUB_QUESTIONS)
    assert f"at most {first_budget} claims" in extraction_prompts[0]
