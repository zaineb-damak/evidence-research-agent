"""End-to-end smoke test against a running stack, through the web proxy.

Usage:
    uv run python -m scripts.smoke_test [base_url] [question]

Exercises what the unit and integration suites fake: real auth, the nginx
proxy, the Celery queue, live providers, the SSE progress stream, and every
result endpoint. Spends one FAST-depth run of LLM and search credits (about
$0.10 at the time of writing). Exits non-zero on the first failed check.
"""

from __future__ import annotations

import json
import sys
import time
import uuid

import httpx

from src.models.progress import ProgressEventType
from src.models.schemas import ResearchDepth

DEFAULT_BASE_URL = "http://127.0.0.1:5173"
DEFAULT_QUESTION = (
    "What are the trade-offs between retrieval-augmented generation and fine-tuning "
    "for giving an LLM domain knowledge?"
)
SMOKE_PASSWORD = "smoke-test-password"
FORGED_TOKEN = "not.a.jwt"
REQUEST_TIMEOUT_SECONDS = 30
STREAM_READ_TIMEOUT_SECONDS = 900
SSE_DATA_PREFIX = "data:"
MIN_REPORT_CHARACTERS = 500
FIRST_CITATION_MARKER = "[1]"

HTTP_OK = 200
HTTP_CREATED = 201
HTTP_UNAUTHORIZED = 401
HTTP_FORBIDDEN = 403
HTTP_NOT_FOUND = 404
HTTP_UNPROCESSABLE = 422
ACCEPTED_CREATE_STATUSES = (HTTP_OK, HTTP_CREATED)
TERMINAL_EVENT_TYPES = (ProgressEventType.DONE.value, ProgressEventType.ERROR.value)
EXIT_FAILURE = 1


def check(label: str, passed: bool, detail: object = "") -> None:
    print(("PASS " if passed else "FAIL ") + label + (f"  ({detail})" if detail != "" else ""))
    if not passed:
        raise SystemExit(EXIT_FAILURE)


def sign_up(client: httpx.Client) -> dict[str, str]:
    email = f"smoke-{uuid.uuid4().hex[:8]}@example.com"
    response = client.post("/auth/signup", json={"email": email, "password": SMOKE_PASSWORD})
    check("signup issues a token", response.status_code == HTTP_CREATED, response.status_code)
    return {"authorization": f"Bearer {response.json()['access_token']}"}


def check_auth_boundaries(client: httpx.Client) -> None:
    anonymous = client.get("/api/research")
    check("anonymous request rejected", anonymous.status_code == HTTP_UNAUTHORIZED)
    forged = client.get("/api/research", headers={"authorization": f"Bearer {FORGED_TOKEN}"})
    check("forged token rejected", forged.status_code == HTTP_UNAUTHORIZED)


def start_research(client: httpx.Client, headers: dict[str, str], question: str) -> str:
    blank = client.post("/api/research", headers=headers, json={"question": " "})
    check("blank question rejected", blank.status_code == HTTP_UNPROCESSABLE, blank.status_code)
    response = client.post(
        "/api/research",
        headers=headers,
        json={"question": question, "depth": ResearchDepth.FAST.value},
    )
    accepted = response.status_code in ACCEPTED_CREATE_STATUSES
    check("research job accepted", accepted, response.status_code)
    return response.json()["research_id"]


def check_ownership(client: httpx.Client, research_id: str) -> None:
    stranger = sign_up(client)
    stranger_view = client.get(f"/api/research/{research_id}", headers=stranger)
    check("another user's job is forbidden", stranger_view.status_code == HTTP_FORBIDDEN)
    unknown = client.get(f"/api/research/{uuid.uuid4()}", headers=stranger)
    check("unknown job is not found", unknown.status_code == HTTP_NOT_FOUND)


def follow_progress(client: httpx.Client, headers: dict[str, str], research_id: str) -> list[str]:
    started_at = time.monotonic()
    event_types: list[str] = []
    timeout = httpx.Timeout(REQUEST_TIMEOUT_SECONDS, read=STREAM_READ_TIMEOUT_SECONDS)
    with client.stream(
        "GET", f"/api/research/{research_id}/events", headers=headers, timeout=timeout
    ) as stream:
        for line in stream.iter_lines():
            if not line.startswith(SSE_DATA_PREFIX):
                continue
            event = json.loads(line[len(SSE_DATA_PREFIX):])
            event_types.append(event["event_type"])
            elapsed = time.monotonic() - started_at
            print(f"  +{elapsed:6.1f}s {event['event_type']:<16} {event.get('stage') or ''}")
            if event["event_type"] in TERMINAL_EVENT_TYPES:
                break
    return event_types


def check_results(client: httpx.Client, headers: dict[str, str], research_id: str) -> None:
    def fetch(path: str) -> httpx.Response:
        return client.get(f"/api/research/{research_id}{path}", headers=headers)

    job = fetch("").json()
    claims = fetch("/claims").json()
    sources = fetch("/sources").json()
    graph = fetch("/graph").json()
    report = fetch("/report").json()
    print(f"cost {job.get('cost')}")
    print(
        f"claims {len(claims)}  sources {len(sources)}  "
        f"graph nodes {len(graph.get('nodes', []))}  edges {len(graph.get('edges', []))}"
    )
    report_text = report.get("report") or ""
    check("report has content", len(report_text) > MIN_REPORT_CHARACTERS, len(report_text))
    check("report carries citations", FIRST_CITATION_MARKER in report_text)


def main(argv: list[str]) -> int:
    base_url = argv[1] if len(argv) > 1 else DEFAULT_BASE_URL
    question = argv[2] if len(argv) > 2 else DEFAULT_QUESTION
    client = httpx.Client(base_url=base_url, timeout=REQUEST_TIMEOUT_SECONDS)

    check_auth_boundaries(client)
    headers = sign_up(client)
    research_id = start_research(client, headers, question)
    print(f"research_id {research_id}")
    check_ownership(client, research_id)

    event_types = follow_progress(client, headers, research_id)
    check("stream opens with a snapshot", event_types[0] == ProgressEventType.SNAPSHOT.value)
    check("pipeline completed", event_types[-1] == ProgressEventType.DONE.value, event_types[-1])
    check_results(client, headers, research_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
