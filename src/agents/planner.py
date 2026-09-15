"""Research Planner: decompose the question into a few high-value sub-questions.

Guards against over-decomposition (§4): prefer differentiating questions over
trivially restating the subject. Caps sub-question count per depth tier.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from src.config import get_settings
from src.llm.base import StructuredLLM
from src.llm.chains import build_structured_chain
from src.llm.usage import token_usage
from src.models.schemas import ResearchDepth, ResearchTask
from src.prompts import PLANNER_PROMPT


class PlanOutput(BaseModel):
    sub_questions: list[str] = Field(default_factory=list)


def plan_research(
    llm: StructuredLLM, question: str, depth: ResearchDepth
) -> tuple[list[ResearchTask], int, int]:
    cap = get_settings().cap_for(depth)
    chain = build_structured_chain(llm, PLANNER_PROMPT, PlanOutput)
    result = chain.invoke(
        {"question": question, "max_sub_questions": cap.max_sub_questions}
    )
    plan: PlanOutput = result["parsed"]
    tokens_in, tokens_out = token_usage(result["raw"])

    sub_questions = [
        text.strip() for text in plan.sub_questions if text.strip()
    ][: cap.max_sub_questions]
    if not sub_questions:
        sub_questions = [question]
    tasks = [ResearchTask(sub_question=text) for text in sub_questions]
    return tasks, tokens_in, tokens_out
