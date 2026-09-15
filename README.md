# Evidence Research Agent

An autonomous research system that decomposes a question, searches multiple
sources, extracts **structured evidence**, builds an **evidence graph**, detects
contradictions, verifies claims, and produces a **citation-backed report**.

> Core principle: generated text is never evidence. Every important claim in the
> final report traces to a source passage.

The differentiator is **research as evidence-graph construction** — not
search → summarize → synthesize.

## Status

Built in stacked branches, one phase per branch.

- **Phase 1 — foundations + walking skeleton.** End-to-end pipeline: planner →
  researcher (8 connectors) → hybrid retrieval → evidence extractor → measurable
  confidence → synthesizer → citation-backed report, over a FastAPI service.
- **Phase 2 — evidence graph.** Entity/claim resolution (merge paraphrases),
  contradiction detection (winner by source quality, never silent), and claim
  verification (VERIFIED / PARTIALLY_SUPPORTED / CONFLICTING / UNSUPPORTED).
- **Phase 3 — production reliability.** Staged pipeline with checkpoint/resume,
  retry + provider fallback, per-key token-bucket rate limiting, token cost
  accounting surfaced in job status, and OpenTelemetry stage tracing.
  Authenticated API (Bearer key, fails closed).

Everything runs on injected dependencies, so the pipeline and API are covered by
tests without any external services.

- **Phase 4 — evaluation.** Benchmark dataset schema + loader, retrieval metrics
  (Recall@k, MRR, nDCG), citation metrics (correctness/completeness, §21 targets),
  generation metrics (topic completeness, groundedness, claim coverage), a
  dependency-injected runner, and a regression gate wired into CI.

- **Phase 5 — security.** SSRF guard re-validated on every redirect hop,
  robots.txt compliance, page-size/document/source/recursion limits, PII
  redaction of untrusted content, and prompt-injection isolation (retrieved text
  is delimited untrusted data, never system instructions).

- **Phase 6 — UI + Evidence Explorer.** React + TypeScript (Vite) app: research
  request form, live progress polling, report viewer, and the **Evidence
  Explorer** — click a claim to see its confidence breakdown, supporting sources,
  contradicting claims, and related claims (all resolved from the evidence
  graph); click through related/contradicting claims to navigate. Typed API
  layer mirrors the Pydantic schemas.

- **Phase 7 — LangChain abstraction.** LLM and embedding initialization go
  through LangChain (`init_chat_model`, `OpenAIEmbeddings`/`VoyageAIEmbeddings`),
  and passage chunking uses LangChain's `RecursiveCharacterTextSplitter`. These
  sit behind the existing `LLMProvider` / `Embedder` seams, so agents and tests
  are unchanged. Structured generation stays prompt-and-parse based for uniform
  behavior across providers (including self-hosted OpenAI-compatible models).

- **Phase 8 — LangGraph pipeline.** The orchestration is now a real LangGraph
  `StateGraph` over `ResearchState`: nodes for plan → search → extract → score →
  verify → synthesize, a conditional edge that skips to synthesis when no
  passages are found, and a compiled checkpointer so an interrupted run resumes
  from the last completed node. `run_pipeline` keeps its signature, so callers
  and tests are unchanged.

- **Phase 9 — full persistence, no in-memory production path.** Jobs and the
  evidence tables live in **Postgres** (SQLAlchemy + Alembic); the API persists a
  queued job and enqueues it on **Redis + Celery**; the worker runs the graph
  with a **LangGraph Postgres checkpointer** and saves the result. Retrieval is
  **Postgres full-text search (keyword) + Qdrant (vectors)** fused with RRF; the
  evidence graph is written to and read from **Neo4j**. In-memory implementations
  remain only as injected test doubles (`InMemoryJobRepository`,
  `InMemoryPassageIndex`, `InMemoryGraphStore`) so the suite runs without Docker.

All phases are implemented as stacked branches
(`phase-1-foundations` … `phase-9-persistence`).

## Architecture

| Layer | Choice |
|---|---|
| API | FastAPI + Pydantic v2 |
| Orchestration | LangGraph `StateGraph` (nodes, conditional edge, checkpointer) |
| Jobs/metadata | PostgreSQL |
| Evidence graph | Neo4j (Cypher) behind `GraphStore` |
| Vectors | Qdrant behind `VectorStore` (Weaviate fallback) |
| Queue/worker | Redis + Celery |
| Search | Tavily (+ arXiv, Semantic Scholar, GitHub, Reddit, YouTube, generic API) |
| LLM | LangChain `init_chat_model` behind an `LLMProvider` seam: OpenAI / Anthropic / Vertex / self-hosted (OpenAI-compatible) |
| Embeddings | LangChain embeddings behind an `Embedder` seam (OpenAI / Voyage) |
| Chunking | LangChain `RecursiveCharacterTextSplitter` |
| Reranker | interface only in v1 (skipped — RRF fusion is the ranker) |

### Confidence is measurable, never an LLM self-rating

```
confidence = source_quality × evidence_strength × source_agreement × extraction_confidence
```

- **source_quality** — §6 score (authority + recency + relevance + primary bonus + corroboration), normalized.
- **evidence_strength** — claim↔passage embedding cosine similarity.
- **source_agreement** — `min(distinct corroborating sources / 3, 1)`.
- **extraction_confidence** — calibrated extraction signal (Phase 2: self-consistency across repeated extractions).

## Quick start

```bash
# 1. Dependencies (uv)
uv venv && uv pip install -e ".[dev]"

# 2. Config
cp .env.example .env        # set LLM_PROVIDER + a key, and TAVILY_API_KEY

# 3. Infra (Postgres, Neo4j, Qdrant, Redis)
docker compose up -d
# Langfuse (LLM tracing) is a managed cloud service — optional; set the
# LANGFUSE_* keys in .env to point at cloud.langfuse.com.

# 4. Run the API
uv run uvicorn apps.api.main:app --reload

# 5. Start a research job
curl -X POST localhost:8000/api/research \
  -H 'content-type: application/json' \
  -d '{"question":"Compare Qwen, Llama and Mistral for customer support","depth":"fast"}'
```

Then poll `GET /api/research/{id}` and read `GET /api/research/{id}/report`.

### Production execution path

```bash
celery -A apps.worker.celery_app worker --loglevel=info
```

## Tests

```bash
uv run pytest          # unit + integration, no external services required
```

## Depth tiers (cost/latency caps)

| depth | sources | claims | sub-questions |
|---|---|---|---|
| fast | 10 | 25 | 5 |
| normal | 25 | 50 | 8 |
| deep | 50 | 100 | 12 |

## Layout

```
src/agents/       planner, researcher, extractor, synthesizer (verifier: Phase 2)
src/retrieval/    keyword, semantic, hybrid (RRF), reranker (stub)
src/evidence/     claims, confidence, citations, graph (resolution/contradiction: Phase 2)
src/sources/      8 connectors + fetcher + quality, behind a common interface
src/stores/       Neo4j graph, Qdrant vectors, Redis cache
src/llm/          provider-agnostic LLM + structured output
src/workflows/    end-to-end pipeline + dependency wiring
apps/api/         FastAPI service     apps/worker/  Celery worker
```
