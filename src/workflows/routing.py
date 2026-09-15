"""Conditional-edge routing for the research StateGraph."""

from __future__ import annotations

from src.models.schemas import ResearchState, WorkflowRoute


def route_after_search(state: ResearchState) -> WorkflowRoute:
    """Skip extraction/scoring/verification when search found no passages."""
    return WorkflowRoute.HAS_PASSAGES if state.passages else WorkflowRoute.NO_PASSAGES
