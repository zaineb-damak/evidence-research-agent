"""Qdrant-backed vector store behind a small interface.

Weaviate is the documented fallback; swapping it means implementing the same
three methods. Points carry payload for metadata filtering (§16).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

PASSAGE_ID_PAYLOAD_KEY = "passage_id"
JOB_ID_PAYLOAD_KEY = "job_id"


@dataclass
class VectorHit:
    passage_id: str
    score: float
    payload: dict


class QdrantVectorStore:
    def __init__(self, url: str, collection: str, dim: int):
        self._client = QdrantClient(url=url)
        self.collection = collection
        self.dim = dim

    def ensure_collection(self) -> None:
        existing_names = {c.name for c in self._client.get_collections().collections}
        if self.collection not in existing_names:
            self._client.create_collection(
                collection_name=self.collection,
                vectors_config=VectorParams(size=self.dim, distance=Distance.COSINE),
            )

    def upsert(self, passage_id: str, vector: list[float], payload: dict) -> str:
        point_id = str(uuid.uuid4())
        point = PointStruct(
            id=point_id,
            vector=vector,
            payload={PASSAGE_ID_PAYLOAD_KEY: passage_id, **payload},
        )
        self._client.upsert(collection_name=self.collection, points=[point])
        return point_id

    def search(
        self, vector: list[float], top_k: int, job_id: str | None = None
    ) -> list[VectorHit]:
        job_filter = None
        if job_id:
            job_filter = Filter(
                must=[FieldCondition(key=JOB_ID_PAYLOAD_KEY, match=MatchValue(value=job_id))]
            )
        response = self._client.query_points(
            collection_name=self.collection,
            query=vector,
            limit=top_k,
            query_filter=job_filter,
            with_payload=True,
        )
        return [
            VectorHit(
                passage_id=hit.payload[PASSAGE_ID_PAYLOAD_KEY],
                score=hit.score,
                payload=hit.payload,
            )
            for hit in response.points
        ]
