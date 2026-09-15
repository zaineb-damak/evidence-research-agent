"""The pipeline graph renders to Mermaid with every node and route."""

from __future__ import annotations

from scripts.generate_graph_diagram import render_mermaid
from src.workflows.nodes import NodeName


def test_mermaid_contains_all_nodes_and_routes():
    mermaid = render_mermaid()
    for node in NodeName:
        assert node.value in mermaid
    assert "has_passages" in mermaid
    assert "no_passages" in mermaid
