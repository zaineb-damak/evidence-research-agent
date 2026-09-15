"""LangGraph node functions and the dependency bundle they operate on.

Each node is a thin wrapper over an agent function: it opens a tracing span,
bills token usage, and returns only the state fields it changed. Orchestration
(graph assembly, compilation, running) lives in src/workflows/research.py.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from langchain_core.embeddings import Embeddings

from src.agents.extractor import extract_claims
from src.agents.planner import plan_research
from src.agents.researcher import run_research
from src.agents.synthesizer import synthesize_report
from src.agents.verifier import run_verification
from src.config import get_settings
from src.evidence.graph import persist_graph
from src.evidence.scoring import merge_entities, score_claim_confidence
from src.llm.base import StructuredLLM
from src.models.schemas import ResearchState, ResearchStatus
from src.observability.tracing import stage_span
from src.reliability.cost import record_usage
from src.retrieval.index import PassageIndex, build_embedded_vectors
from src.retrieval.pipeline import retrieve_top_passages
from src.sources.base import SourceConnector
from src.stores.graph import GraphStore
from src.workflows.cost import billed_cost

TOP_PASSAGES_PER_TASK = 6


class NodeName(StrEnum):
    PLAN = "plan"
    SEARCH = "search"
    EXTRACT = "extract"
    SCORE = "score"
    VERIFY = "verify"
    SYNTHESIZE = "synthesize"


@dataclass
class Deps:
    llm: StructuredLLM
    embeddings: Embeddings
    connectors: dict[object, SourceConnector]
    passage_index: PassageIndex
    graph_store: GraphStore


def plan_node(state: ResearchState, deps: Deps) -> dict[str, Any]:
    with stage_span(NodeName.PLAN):
        tasks, tokens_in, tokens_out = plan_research(
            deps.llm, state.original_question, state.depth
        )
    return {
        "research_tasks": tasks,
        "status": ResearchStatus.PLANNING,
        "cost": billed_cost(state.cost, deps.llm.model, tokens_in, tokens_out),
    }


def search_node(state: ResearchState, deps: Deps) -> dict[str, Any]:
    with stage_span(NodeName.SEARCH):
        research_output = run_research(state.research_tasks, deps.connectors, state.depth)
        passage_vectors = build_embedded_vectors(deps.embeddings, research_output.passages)
        if research_output.passages:
            deps.passage_index.add_passages(
                state.research_id, research_output.passages, passage_vectors
            )
    return {
        "sources": research_output.sources,
        "documents": research_output.documents,
        "passages": research_output.passages,
        "passage_vectors": passage_vectors,
        "status": ResearchStatus.SEARCHING,
    }


def extract_node(state: ResearchState, deps: Deps) -> dict[str, Any]:
    claim_cap = get_settings().cap_for(state.depth).max_claims
    source_id_by_passage = {passage.id: passage.source_id for passage in state.passages}
    passage_text_by_id = {passage.id: passage.text for passage in state.passages}

    claims = list(state.claims)
    evidence = list(state.evidence)
    entities = list(state.entities)
    cost = state.cost.model_copy(deep=True)

    with stage_span(NodeName.EXTRACT):
        for task in state.research_tasks:
            top_passage_ids = retrieve_top_passages(
                state.research_id,
                task.sub_question,
                deps.passage_index,
                deps.embeddings,
                top_k=TOP_PASSAGES_PER_TASK,
            )
            selected_passages = [
                (passage_id, source_id_by_passage[passage_id], passage_text_by_id[passage_id])
                for passage_id in top_passage_ids
                if passage_id in passage_text_by_id
            ]
            extraction, tokens_in, tokens_out = extract_claims(
                deps.llm, selected_passages, claim_cap
            )
            record_usage(cost, deps.llm.model, tokens_in, tokens_out)
            claims.extend(extraction.claims)
            evidence.extend(extraction.evidence)
            merge_entities(entities, extraction.entities)
            if len(claims) >= claim_cap:
                break

    return {
        "claims": claims[:claim_cap],
        "evidence": evidence,
        "entities": entities,
        "cost": cost,
        "status": ResearchStatus.EXTRACTING,
    }


def score_node(state: ResearchState, deps: Deps) -> dict[str, Any]:
    with stage_span(NodeName.SCORE):
        score_claim_confidence(
            state.claims,
            state.evidence,
            state.sources,
            state.passage_vectors,
            deps.embeddings,
        )
    return {
        "claims": state.claims,
        "evidence": state.evidence,
        "sources": state.sources,
        "status": ResearchStatus.RESOLVING,
    }


def verify_node(state: ResearchState, deps: Deps) -> dict[str, Any]:
    with stage_span(NodeName.VERIFY):
        tokens_in, tokens_out = run_verification(deps.llm, deps.embeddings, state)
    return {
        "claims": state.claims,
        "evidence": state.evidence,
        "contradictions": state.contradictions,
        "cost": billed_cost(state.cost, deps.llm.model, tokens_in, tokens_out),
        "status": ResearchStatus.VERIFYING,
    }


def synthesize_node(state: ResearchState, deps: Deps) -> dict[str, Any]:
    with stage_span(NodeName.SYNTHESIZE):
        report, tokens_in, tokens_out = synthesize_report(deps.llm, state)
        # Persist the evidence graph now that claims/contradictions are final.
        persist_graph(deps.graph_store, state)
    return {
        "report": report,
        "cost": billed_cost(state.cost, deps.llm.model, tokens_in, tokens_out),
        "status": ResearchStatus.COMPLETED,
    }
