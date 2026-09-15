"""API surface test.

Overrides the persistence dependencies with in-memory doubles and a synchronous
enqueuer that runs the pipeline with fakes, so the full request lifecycle and
authentication are exercised without Postgres/Neo4j/Redis.
"""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from apps.api import dependencies, main  # noqa: E402
from apps.api.routes_auth import get_user_repository  # noqa: E402
from src.config import Settings, get_settings  # noqa: E402
from src.db.repository import InMemoryJobRepository  # noqa: E402
from src.db.users import InMemoryUserRepository  # noqa: E402
from src.workflows.research import run_pipeline  # noqa: E402
from tests.conftest import make_deps  # noqa: E402

TEST_JWT_SECRET = "test-secret-that-is-at-least-32-bytes-long"
TEST_EMAIL = "researcher@example.com"
TEST_PASSWORD = "correct horse battery staple"


@pytest.fixture
def client(fake_llm, fake_embedder, fake_connectors):
    repository = InMemoryJobRepository()
    users = InMemoryUserRepository()
    users.create(TEST_EMAIL, TEST_PASSWORD)
    deps, _index, graph_store = make_deps(fake_llm, fake_embedder, fake_connectors)

    def run_synchronously(research_id: str) -> None:
        state = repository.get(research_id)
        run_pipeline(state, deps)
        repository.save(state)

    main.app.dependency_overrides[get_settings] = lambda: Settings(jwt_secret=TEST_JWT_SECRET)
    main.app.dependency_overrides[dependencies.get_repository] = lambda: repository
    main.app.dependency_overrides[dependencies.get_graph_store] = lambda: graph_store
    main.app.dependency_overrides[dependencies.get_job_enqueuer] = lambda: run_synchronously
    main.app.dependency_overrides[get_user_repository] = lambda: users
    yield TestClient(main.app)
    main.app.dependency_overrides.clear()


def _auth_headers(client) -> dict[str, str]:
    resp = client.post(
        "/auth/token", json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
    )
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def test_login_issues_token(client):
    headers = _auth_headers(client)
    assert headers["Authorization"].startswith("Bearer ")


def test_login_with_wrong_password_rejected(client):
    resp = client.post(
        "/auth/token", json={"email": TEST_EMAIL, "password": "nope"}
    )
    assert resp.status_code == 401


def test_research_lifecycle(client):
    AUTH_HEADERS = _auth_headers(client)
    resp = client.post(
        "/api/research",
        json={"question": "What context length does Model X support?", "depth": "fast"},
        headers=AUTH_HEADERS,
    )
    assert resp.status_code == 200
    research_id = resp.json()["research_id"]

    status = client.get(f"/api/research/{research_id}", headers=AUTH_HEADERS).json()
    assert status["status"] == "completed"
    assert status["counts"]["claims"] >= 1
    assert status["cost"]["usd"] >= 0.0

    report = client.get(f"/api/research/{research_id}/report", headers=AUTH_HEADERS).json()
    assert "# Research Report" in report["report"]

    graph = client.get(f"/api/research/{research_id}/graph", headers=AUTH_HEADERS).json()
    assert any(node["label"] == "Claim" for node in graph["nodes"])
    assert any(edge["rel"] == "SUPPORTS" for edge in graph["edges"])


def test_unknown_job_returns_404(client):
    headers = _auth_headers(client)
    assert client.get("/api/research/nope", headers=headers).status_code == 404


def test_requests_without_token_are_rejected(client):
    unauthenticated = client.post(
        "/api/research",
        json={"question": "anything", "depth": "fast"},
    )
    assert unauthenticated.status_code == 401


def test_requests_with_invalid_token_are_rejected(client):
    resp = client.get(
        "/api/research/whatever",
        headers={"Authorization": "Bearer not-a-real-jwt"},
    )
    assert resp.status_code == 401
