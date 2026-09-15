"""Project ResearchState into the evidence graph (§8).

`project_graph` builds an in-memory {nodes, edges} view used by GET /graph and
the Evidence Explorer. `persist_graph` writes the same shape into Neo4j via the
GraphStore when one is available. Keeping both here means the graph shape has a
single definition.
"""

from __future__ import annotations

from typing import Any

from src.models.schemas import GraphLabel, GraphRelation, ResearchState
from src.stores.graph import GraphNode, GraphStore


def project_graph(state: ResearchState) -> dict[str, list[dict[str, Any]]]:
    nodes: list[dict] = []
    edges: list[dict] = []

    for source in state.sources:
        nodes.append({"label": GraphLabel.SOURCE, "ref_id": source.id,
                      "props": {"title": source.title or source.url, "type": source.source_type}})
    for entity in state.entities:
        nodes.append({"label": GraphLabel.ENTITY, "ref_id": entity.id,
                      "props": {"name": entity.name}})
    for claim in state.claims:
        nodes.append({"label": GraphLabel.CLAIM, "ref_id": claim.id,
                      "props": {"text": claim.text, "status": claim.status,
                                "confidence": claim.confidence}})
        if claim.subject_entity_id:
            edges.append({"src": claim.id, "rel": GraphRelation.ABOUT,
                          "dst": claim.subject_entity_id})

    evidence_by_id = {evidence.id: evidence for evidence in state.evidence}
    for claim in state.claims:
        for evidence_id in claim.evidence_ids:
            evidence = evidence_by_id.get(evidence_id)
            if evidence:
                edges.append({"src": claim.id, "rel": GraphRelation.SUPPORTS,
                              "dst": evidence.source_id,
                              "meta": {"similarity": evidence.similarity}})
    for contradiction in state.contradictions:
        edges.append({"src": contradiction.claim_a_id, "rel": GraphRelation.CONTRADICTS,
                      "dst": contradiction.claim_b_id,
                      "meta": {"rationale": contradiction.rationale}})

    return {"nodes": nodes, "edges": edges}


def persist_graph(store: GraphStore, state: ResearchState) -> None:
    graph = project_graph(state)
    for node in graph["nodes"]:
        store.upsert_node(
            GraphNode(label=node["label"], ref_id=node["ref_id"], props=node["props"]),
            job_id=state.research_id,
        )
    for edge in graph["edges"]:
        store.add_relationship(edge["src"], edge["rel"], edge["dst"], edge.get("meta"))
