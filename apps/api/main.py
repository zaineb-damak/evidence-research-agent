"""FastAPI surface (§24).

POST /api/research persists a queued job (owned by the caller) and enqueues it on
Celery; the GET endpoints read job state from Postgres and the evidence graph from
Neo4j. Every route requires a valid JWT bearer token (see apps/api/auth.py), and
callers may only read their own jobs. POST /auth/token issues tokens.
"""

from __future__ import annotations

from fastapi import Depends, FastAPI

from apps.api.auth import AuthContext, require_user
from apps.api.dependencies import (
    JobEnqueuer,
    get_graph_store,
    get_job_enqueuer,
    get_repository,
)
from apps.api.jobs import require_owned_job
from apps.api.routes_auth import router as auth_router
from src.db.repository import JobRepository
from src.models.schemas import ResearchRequest
from src.stores.graph import GraphStore

API_TITLE = "Evidence Research Agent"
API_VERSION = "0.1.0"

app = FastAPI(title=API_TITLE, version=API_VERSION)
app.include_router(auth_router)


@app.post("/api/research")
def create_research(
    request: ResearchRequest,
    repository: JobRepository = Depends(get_repository),
    enqueue: JobEnqueuer = Depends(get_job_enqueuer),
    auth: AuthContext = Depends(require_user),
) -> dict:
    state = repository.create(
        request, owner_user_id=auth.user_id, owner_session_id=auth.session_id
    )
    enqueue(state.research_id)
    return {"research_id": state.research_id, "status": state.status}


@app.get("/api/research/{research_id}")
def get_research(
    research_id: str,
    repository: JobRepository = Depends(get_repository),
    auth: AuthContext = Depends(require_user),
) -> dict:
    state = require_owned_job(repository, research_id, auth)
    return {
        "research_id": state.research_id,
        "question": state.original_question,
        "status": state.status,
        "error": state.error,
        "counts": {
            "sources": len(state.sources),
            "passages": len(state.passages),
            "claims": len(state.claims),
            "contradictions": len(state.contradictions),
        },
        "cost": state.cost.model_dump(),
    }


@app.get("/api/research/{research_id}/claims")
def get_claims(
    research_id: str,
    repository: JobRepository = Depends(get_repository),
    auth: AuthContext = Depends(require_user),
) -> list[dict]:
    state = require_owned_job(repository, research_id, auth)
    return [claim.model_dump() for claim in state.claims]


@app.get("/api/research/{research_id}/sources")
def get_sources(
    research_id: str,
    repository: JobRepository = Depends(get_repository),
    auth: AuthContext = Depends(require_user),
) -> list[dict]:
    state = require_owned_job(repository, research_id, auth)
    return [source.model_dump() for source in state.sources]


@app.get("/api/research/{research_id}/graph")
def get_graph(
    research_id: str,
    repository: JobRepository = Depends(get_repository),
    graph_store: GraphStore = Depends(get_graph_store),
    auth: AuthContext = Depends(require_user),
) -> dict:
    # 404/403 if the job is unknown or not the caller's; otherwise read the graph.
    require_owned_job(repository, research_id, auth)
    return graph_store.subgraph(research_id)


@app.get("/api/research/{research_id}/report")
def get_report(
    research_id: str,
    repository: JobRepository = Depends(get_repository),
    auth: AuthContext = Depends(require_user),
) -> dict:
    state = require_owned_job(repository, research_id, auth)
    return {"research_id": state.research_id, "status": state.status, "report": state.report}
