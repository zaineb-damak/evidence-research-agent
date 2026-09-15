"""Neo4j-backed evidence graph (§8) behind a small GraphStore interface.

Nodes carry (label, ref_id, job_id); ref_id joins back to the Postgres row.
Relationships are the §8 verbs. Cypher powers Evidence Explorer traversals and
contradiction queries.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from neo4j import GraphDatabase

from src.exceptions import InvalidRelationshipError
from src.models.schemas import GraphLabel, GraphRelation

# Derived from the domain enums so the label/relation vocabulary has one home.
VALID_RELS = {relation.value for relation in GraphRelation}

# Node labels that carry a uniqueness constraint on ref_id.
CONSTRAINED_LABELS = tuple(label.value for label in GraphLabel)


@dataclass
class GraphNode:
    label: str
    ref_id: str
    props: dict


@runtime_checkable
class GraphStore(Protocol):
    def ensure_constraints(self) -> None: ...

    def upsert_node(self, node: GraphNode, job_id: str) -> None: ...

    def add_relationship(
        self, src_ref: str, rel: str, dst_ref: str, meta: dict | None = None
    ) -> None: ...

    def subgraph(self, job_id: str) -> dict: ...


class Neo4jGraphStore:
    def __init__(self, uri: str, user: str, password: str):
        self._driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self) -> None:
        self._driver.close()

    def ensure_constraints(self) -> None:
        stmts = [
            f"CREATE CONSTRAINT {label.lower()}_ref IF NOT EXISTS "
            f"FOR (n:{label}) REQUIRE (n.ref_id) IS UNIQUE"
            for label in CONSTRAINED_LABELS
        ]
        with self._driver.session() as session:
            for stmt in stmts:
                session.run(stmt)

    def upsert_node(self, node: GraphNode, job_id: str) -> None:
        with self._driver.session() as session:
            session.run(
                f"MERGE (n:{node.label} {{ref_id: $ref_id}}) "
                "SET n += $props, n.job_id = $job_id",
                ref_id=node.ref_id,
                props=node.props,
                job_id=job_id,
            )

    def add_relationship(
        self, src_ref: str, rel: str, dst_ref: str, meta: dict | None = None
    ) -> None:
        if rel not in VALID_RELS:
            raise InvalidRelationshipError(rel)
        with self._driver.session() as session:
            session.run(
                "MATCH (a {ref_id: $src}), (b {ref_id: $dst}) "
                f"MERGE (a)-[r:{rel}]->(b) SET r += $meta",
                src=src_ref,
                dst=dst_ref,
                meta=meta or {},
            )

    def subgraph(self, job_id: str) -> dict:
        """Return {nodes, edges} for the Evidence Explorer / GET /graph."""
        with self._driver.session() as session:
            nodes = session.run(
                "MATCH (n {job_id: $job_id}) "
                "RETURN labels(n)[0] AS label, n.ref_id AS ref_id, properties(n) AS props",
                job_id=job_id,
            ).data()
            edges = session.run(
                "MATCH (a {job_id: $job_id})-[r]->(b {job_id: $job_id}) "
                "RETURN a.ref_id AS src, type(r) AS rel, b.ref_id AS dst, properties(r) AS meta",
                job_id=job_id,
            ).data()
        return {"nodes": nodes, "edges": edges}


class InMemoryGraphStore:
    """Test double: keeps nodes/edges per job in process memory."""

    def __init__(self) -> None:
        self._nodes_by_job: dict[str, dict[str, dict]] = {}
        self._edges_by_job: dict[str, dict[tuple[str, str, str], dict]] = {}

    def ensure_constraints(self) -> None:
        return None

    def upsert_node(self, node: GraphNode, job_id: str) -> None:
        self._nodes_by_job.setdefault(job_id, {})[node.ref_id] = {
            "label": node.label,
            "ref_id": node.ref_id,
            "props": node.props,
        }

    def add_relationship(
        self, src_ref: str, rel: str, dst_ref: str, meta: dict | None = None
    ) -> None:
        if rel not in VALID_RELS:
            raise InvalidRelationshipError(rel)
        job_id = self._job_of_node(src_ref)
        if job_id is None:
            return
        self._edges_by_job.setdefault(job_id, {})[(src_ref, rel, dst_ref)] = {
            "src": src_ref,
            "rel": rel,
            "dst": dst_ref,
            "meta": meta or {},
        }

    def subgraph(self, job_id: str) -> dict:
        return {
            "nodes": list(self._nodes_by_job.get(job_id, {}).values()),
            "edges": list(self._edges_by_job.get(job_id, {}).values()),
        }

    def _job_of_node(self, ref_id: str) -> str | None:
        for job_id, nodes in self._nodes_by_job.items():
            if ref_id in nodes:
                return job_id
        return None
