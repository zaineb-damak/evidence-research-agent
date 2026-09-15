"""QdrantVectorStore.search maps the current qdrant-client API.

The pipeline tests use the in-memory passage index, so the real Qdrant adapter
is otherwise unexercised — this pins it to the `query_points` API (a `.search`
removal in qdrant-client is exactly what slipped through before).
"""

from __future__ import annotations

from dataclasses import dataclass

from src.stores.vector import QdrantVectorStore


@dataclass
class _FakePoint:
    payload: dict
    score: float


class _FakeResponse:
    def __init__(self, points):
        self.points = points


class _FakeQdrantClient:
    def __init__(self):
        self.last_query_kwargs: dict | None = None

    def query_points(self, **kwargs):
        self.last_query_kwargs = kwargs
        return _FakeResponse(
            [
                _FakePoint(payload={"passage_id": "p1", "job_id": "job1"}, score=0.9),
                _FakePoint(payload={"passage_id": "p2", "job_id": "job1"}, score=0.5),
            ]
        )


def _store_with_fake_client() -> tuple[QdrantVectorStore, _FakeQdrantClient]:
    store = QdrantVectorStore(url="http://localhost:6333", collection="c", dim=3)
    fake = _FakeQdrantClient()
    store._client = fake  # noqa: SLF001 — adapter test needs to inject the client
    return store, fake


def test_search_uses_query_points_and_maps_hits():
    store, fake = _store_with_fake_client()

    hits = store.search([0.1, 0.2, 0.3], top_k=5, job_id="job1")

    # Called the current API with the right arguments.
    assert fake.last_query_kwargs["collection_name"] == "c"
    assert fake.last_query_kwargs["query"] == [0.1, 0.2, 0.3]
    assert fake.last_query_kwargs["limit"] == 5
    assert fake.last_query_kwargs["with_payload"] is True
    assert fake.last_query_kwargs["query_filter"] is not None  # job filter applied

    # Mapped ScoredPoints to VectorHits in order.
    assert [hit.passage_id for hit in hits] == ["p1", "p2"]
    assert hits[0].score == 0.9


def test_search_without_job_id_has_no_filter():
    store, fake = _store_with_fake_client()
    store.search([0.0, 0.0, 0.0], top_k=3)
    assert fake.last_query_kwargs["query_filter"] is None
