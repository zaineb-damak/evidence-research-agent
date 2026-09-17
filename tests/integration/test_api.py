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


def test_signup_creates_account_and_issues_token(client):
    resp = client.post(
        "/auth/signup",
        json={"email": "new.researcher@example.com", "password": "a very good passphrase"},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]

    # The issued token authenticates like any other.
    headers = {"Authorization": f"Bearer {body['access_token']}"}
    resp = client.get("/api/research", headers=headers)
    assert resp.status_code == 200
    assert resp.json() == []


def test_signup_with_duplicate_email_is_rejected(client):
    resp = client.post(
        "/auth/signup",
        json={"email": TEST_EMAIL, "password": "another good passphrase"},
    )
    assert resp.status_code == 409


def test_signup_with_short_password_is_rejected(client):
    resp = client.post(
        "/auth/signup",
        json={"email": "short.password@example.com", "password": "short"},
    )
    assert resp.status_code == 422


def test_list_research_returns_only_callers_jobs(client):
    headers = _auth_headers(client)
    client.post(
        "/api/research",
        json={"question": "What context length does Model X support?", "depth": "fast"},
        headers=headers,
    )

    resp = client.get("/api/research", headers=headers)
    assert resp.status_code == 200
    jobs = resp.json()
    assert len(jobs) == 1
    assert jobs[0]["question"] == "What context length does Model X support?"
    assert jobs[0]["status"] == "completed"
    assert "created_at" in jobs[0]
    assert "updated_at" in jobs[0]


def test_list_research_requires_auth(client):
    resp = client.get("/api/research")
    assert resp.status_code == 401


def _sse_events(text: str) -> list[tuple[str, str]]:
    """Parse `event: X\\ndata: Y\\n\\n` framing into (event_name, data) pairs."""
    events = []
    for block in text.strip().split("\n\n"):
        if not block:
            continue
        lines = block.splitlines()
        event_name = lines[0].removeprefix("event: ")
        data = lines[1].removeprefix("data: ")
        events.append((event_name, data))
    return events


def test_events_stream_yields_snapshot_then_terminal_event_for_finished_job(client):
    # run_synchronously (the test enqueuer) already finishes the job before
    # POST /api/research returns, so this must not hang waiting on Redis.
    headers = _auth_headers(client)
    resp = client.post(
        "/api/research",
        json={"question": "What context length does Model X support?", "depth": "fast"},
        headers=headers,
    )
    research_id = resp.json()["research_id"]

    resp = client.get(f"/api/research/{research_id}/events", headers=headers)
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")

    events = _sse_events(resp.text)
    assert [name for name, _ in events] == ["snapshot", "done"]
    for _, data in events:
        assert '"status":"completed"' in data


def test_events_stream_requires_auth(client):
    resp = client.get("/api/research/whatever/events")
    assert resp.status_code == 401


def test_events_stream_unknown_job_returns_404(client):
    headers = _auth_headers(client)
    resp = client.get("/api/research/nope/events", headers=headers)
    assert resp.status_code == 404
