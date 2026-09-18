# CLAUDE.md — evidence-research-agent

Guidance for working in this repo. Read before editing.

## Project

Autonomous research system that decomposes a question, searches multiple
sources, extracts **structured evidence**, builds an **evidence graph** (Neo4j),
detects contradictions, verifies claims, and produces a **citation-backed
report**. Core principle: generated text is never evidence — every important
claim traces to a source passage.

Built in stacked branches, one phase per branch:
`phase-1-foundations` → `phase-2-evidence-graph` → `phase-3-production` → …

## Coding rules (enforced)

1. **No magic values.** Every literal that isn't trivially self-evident must be a
   named module-level constant or an enum member. No bare numbers or strings in
   logic (thresholds, limits, weights, model ids, status strings).
2. **All imports at the top of the file.** No inline/function-local imports.
   The one exception: a genuinely optional third-party SDK (e.g. Vertex,
   Voyage) may be imported lazily, and must carry a comment saying why.
3. **Clear, self-explanatory names.** No abbreviations that aren't obvious. A
   reader should understand a variable from its name without context.
4. **All API endpoints require authentication.** Every data route depends on
   `require_user` (JWT) from `apps/api/auth.py`. The unauthenticated routes are
   `POST /auth/token`, which issues the token; `POST /auth/signup`, which
   creates an account and auto-issues one; and the three operational routes in
   `apps/api/routes_health.py` — `GET /health/live`, `GET /health/ready` and
   `GET /metrics`. The kubelet cannot present a JWT when probing a pod and
   Prometheus scrapes without a user identity; those routes expose no research
   data and the Ingress never routes to them.
5. **Structured, clean code.** Small, single-responsibility functions.
6. **Helper functions live in separate files.** Keep agents/workflows focused on
   orchestration; put reusable helpers in their own module (e.g. `src/text/`,
   `src/reliability/`), not as private functions scattered in business logic.
   Node bodies, cost billing, routing, prompt/report formatting, source mapping,
   tokenization, and hashing all live in their own modules — see the layout below.
7. **LangChain-first.** Prefer LangChain's own abstractions over hand-rolled
   equivalents. Do not reintroduce a custom prompt builder, JSON-parse-retry
   loop, retry helper, rate limiter, or cache — use the primitives named in
   "LangChain conventions" below.

## Layout

```
src/agents/       planner, researcher, extractor, verifier, synthesizer
src/prompts.py    all ChatPromptTemplates (central)
src/retrieval/    keyword, semantic, hybrid (RRF), reranker (stub)
src/evidence/     claims, confidence, citations, graph, resolution, contradiction,
                  verification, report_format, source_selection
src/sources/      connectors + fetcher + quality + mapping, behind a common interface
src/stores/       Neo4j graph, Qdrant vectors
src/reliability/  cost/pricing (retry/rate-limit/cache now via LangChain built-ins)
src/llm/          base (StructuredLLM) + factory + chains + usage + caching
src/embeddings/   LangChain Embeddings factory (no wrapper)
src/text/         hashing, tokenize, nested
src/exceptions.py central exception hierarchy + messages
src/health/      dependency probes behind GET /health/ready
src/observability/ OTel tracing + Langfuse handler + structlog logging + Prometheus metrics
src/realtime/     Redis pub/sub channel naming + transport for live progress events
src/workflows/    graph assembly (research) + nodes + progress_emitter + cost + routing
                  + checkpoint + deps
apps/api/         FastAPI service (JWT-authenticated) + auth + routes_auth + routes_health
                  + jobs + events + middleware (request id, access log, HTTP metrics)
apps/worker/      Celery worker + progress sink
apps/web/         React UI ("Lantern" design system) + runtimeConfig (runtime API base URL)
scripts/          create_user, generate_graph_diagram
infra/docker/     python.Dockerfile (targets: api, worker), web.Dockerfile, nginx config
infra/k8s/chart/  Helm chart — the deployment target
.github/          CI, release/deploy, security workflows + helm-deploy.sh
```

## LangChain conventions (Phase 8)

The LLM layer is native LangChain — there is no custom `LLMProvider`/`complete()`
seam or `generate_structured` loop:

- **Prompts** are `ChatPromptTemplate`s, all in `src/prompts.py`. Untrusted
  retrieved text is wrapped with `wrap_untrusted` (`src/security/injection.py`)
  and passed as a template *input value*, never interpolated into the template
  string. `UNTRUSTED_SYSTEM_NOTE` also lives in `src/prompts.py`.
- **Structured output**: agents build chains with
  `build_structured_chain(llm, prompt, schema)` (`src/llm/chains.py`), which is
  `prompt | chat_model.with_structured_output(schema, include_raw=True, method=…)`
  with `.with_retry(...)`. Read `result["parsed"]` for the model and
  `token_usage(result["raw"])` (`src/llm/usage.py`) for the cost meter.
- **Provider method policy**: `structured_output_method` maps self-hosted
  `oai_compat` → `json_mode` (no reliable tool calling) and OpenAI/Anthropic/
  Vertex → `function_calling`.
- **`StructuredLLM`** (`src/llm/base.py`) is a logic-free bundle of chat model +
  method + retry count + model id; it is what agents receive and what `Deps.llm`
  holds. `build_llm` (`src/llm/factory.py`) constructs it and attaches an
  `InMemoryRateLimiter` when `llm_requests_per_second > 0`.
- **Embeddings** are LangChain `Embeddings` used directly
  (`embed_documents`/`embed_query`); there is no `Embedder` wrapper.
  `Deps.embeddings` holds it; `dim` comes from `settings.embed_dim`.
- **Caching**: `configure_llm_cache` (`src/llm/caching.py`) calls
  `set_llm_cache` (memory / redis / none by `llm_cache_backend`); the worker
  calls it at startup.
- **Retrieval deliberately keeps custom RRF + `PassageIndex`** (not
  `EnsembleRetriever`) — the index is the single writer of the `passages` table
  and has a Postgres-FTS keyword arm; a LangChain retriever would break that
  invariant.

## Config, auth, observability (Phase 8)

- **Config** (`src/config.py`) reads env via `python-decouple` into a validated
  `Settings` model (`get_settings()`); constructing `Settings(...)` directly (in
  tests) uses defaults + overrides. Never read `os.environ`. Connector base URLs
  are settings, not module constants.
- **Auth is JWT** (`apps/api/auth.py`): `POST /auth/token` issues an HS256 token
  with `sub` (user id) + `sid` (session id); `require_user` returns an
  `AuthContext`. Users live in `src/db/users.py` (bcrypt via
  `src/security/passwords.py`); create one with `python -m scripts.create_user`.
  Jobs are owned (`owner_user_id`/`owner_session_id`) and `require_owned_job`
  (`apps/api/jobs.py`) enforces access (404 unknown / 403 not yours).
- **Checkpoint threads** are scoped `user:session:research_id` via
  `compose_thread_id` (`src/workflows/checkpoint.py`), configurable with
  `checkpoint_thread_scope`.
- **Observability**: `build_langfuse_handler` (`src/observability/langfuse.py`)
  returns a Langfuse callback when keys are set (else `None`); the worker passes
  `langfuse_callbacks(settings)` into `run_pipeline`. OTel stage spans remain.
- **Exceptions** live in `src/exceptions.py` (`ResearchAgentError` + subclasses
  with message templates); the API maps them to HTTP responses.
- **Enums**: `GraphLabel`/`GraphRelation` are the single source of truth for the
  graph vocabulary (the store derives `VALID_RELS`/`CONSTRAINED_LABELS` from
  them); also `EntityType` and `WorkflowRoute`. `DEPTH_CAPS` is keyed by
  `ResearchDepth`.
- **Pipeline diagram**: `python -m scripts.generate_graph_diagram` regenerates
  `docs/pipeline-graph.md` (Mermaid).
- **Live progress**: `run_pipeline` (`src/workflows/research.py`) runs the graph
  with `compiled_graph.stream(state, config, stream_mode=["updates", "custom"])`
  instead of `.invoke()`, accumulating `updates` payloads into the returned
  state and forwarding both `updates` (as `STAGE_COMPLETED` events) and
  `custom` (already-built `ProgressEvent`s from `src/workflows/progress_emitter.py`,
  via LangGraph's `get_stream_writer()`) to an optional `on_progress_event`
  sink. The worker's sink (`apps/worker/progress.py`) writes the cheap
  `research_jobs.status`/`progress_detail` columns
  (`JobRepository.update_progress`) and publishes on a per-job Redis channel
  (`src/realtime/`); `GET /api/research/{id}/events` (`apps/api/events.py`)
  streams those as SSE, authenticated like every other route, starting with a
  `SNAPSHOT` of the persisted state so a client reconnecting mid-run or after
  completion is never stuck waiting.

## Deployment (Phase 9)

Kubernetes is the deployment target; `docker compose` is for development and for
smoke-testing the images CI publishes. Fuller notes live in `docs/DEPLOYMENT.md`
and `docs/DEPLOYMENT_WALKTHROUGH.md` — both local-only, since `docs/` is
gitignored, so treat this section as the tracked source of truth.

- **Images** — `infra/docker/python.Dockerfile` builds both `api` and `worker`
  from one file via `--target`, so they share every layer up to `runtime`.
  `infra/docker/web.Dockerfile` builds the SPA and serves it from
  nginx-unprivileged. Migrations reuse the **api** image with
  `alembic upgrade head`; there is no separate migration image.
- **Everything runs non-root with a read-only root filesystem.** Anything that
  writes gets an explicit `emptyDir` — this is why the web image has nginx
  return `/config.js` from its config instead of writing the file.
- **One image per environment, not one per deploy target.** The web bundle
  holds no environment-specific values: the API base URL arrives at runtime via
  `/config.js` (`apps/web/src/runtimeConfig.ts`). Empty means same-origin, which
  is the default — nginx proxies `/api` and `/auth` to the API Service, so the
  browser never needs CORS.
- **Probes** — liveness (`/health/live`) must never touch a dependency, or one
  database blip restarts every pod; readiness (`/health/ready`) probes all four
  stores concurrently under a single shared deadline (`src/health/checks.py`).
  The worker has no HTTP server, so its readiness is a TCP check on the metrics
  port and its liveness is `celery inspect ping`.
- **Migrations run as a Helm `pre-upgrade` hook**, before the new pods roll.
  `--atomic` cannot un-run a migration, so every migration must be backward
  compatible with the release already running (expand/contract). On the first
  install the hook is `post-install` instead: a pre-install hook runs before
  any release object exists and hangs waiting for its own ServiceAccount,
  Secrets and Postgres.
- **Config plumbing** — settings reach pods through a ConfigMap plus two
  Secrets: `-connection` is always chart-owned and holds values the chart
  *derives* (the Postgres DSN, the Neo4j password) so a workload never knows
  whether a store is in-cluster or managed; `-credentials` holds API keys and
  is replaced by `secrets.existingSecret` anywhere shared.
- **The in-chart datastores are for development and staging only** — single
  replica, no failover, no backups. `values-prod.yaml` disables all four and
  points at managed endpoints, with `REPLACE_ME` placeholders that
  `.github/scripts/helm-deploy.sh` refuses to deploy.

## Web UI (Phase 10)

`apps/web/` implements the "Lantern" handoff in
`design_handoff_research_agent/` (untracked bundle; the README there is the
spec). Rules that keep it consistent:

- **Tokens first.** `src/styles/tokens.css` is the only file holding color,
  type, spacing, radius, shadow or size literals; spacing/radius tokens are
  named by pixel value (`--space-13`). Stylesheets are plain CSS with BEM-ish
  class names, one per area (`shell`, `auth`, `research`, `report`).
- **Shell.** `AppShell` is sidebar + main column; each page renders its own
  `MainHeader` (title, status pill, Share/Export) because the title is page
  state. Below 768px the sidebar is an overlay drawer, opened from the header
  through `SidebarContext`.
- **Pure helpers, not component logic**: `lib/sessionGroups.ts` (history
  filtering + Today / Previous 7 days / Older), `lib/planSteps.ts` (the six
  pipeline stages folded into the plan card's five steps),
  `lib/sourceCards.ts`, `lib/citationMarkers.ts` (remark plugin raising
  `[1] [2]` into superscripts, skipping the report's Sources section).
- **Icons** are `lucide-react` at `ICON_STROKE_WIDTH`; the brand mark,
  favicons and avatar stay placeholder shapes until real assets exist.
- **Deliberate deviations from the handoff** (no backend for them): no OAuth
  buttons, no "Forgot?" link, no signup Name field, no plan/quota line
  (the account footer shows the real run count), Share/Export rendered
  disabled, and a follow-up starts a new run carrying the current run's
  depth. Copy that asserted untrue things (free-run quota, editing a plan
  mid-run, Terms/Privacy) was cut or reworded.

## Testing

`uv run pytest` — unit + integration run with injected fakes, no external
services required. Every new capability ships with a test. The LLM fake is a
LangChain `BaseChatModel` supporting `with_structured_output` (`tests/conftest.py`:
`FakeChatModel`, `structured_llm`, `DeterministicEmbeddings`).

## Conventions

- Settings come from `src/config.py` (pydantic-settings); never read
  `os.environ` directly.
- Timestamps via `src/clock.py` (naive UTC), never `datetime.utcnow()`.
- Lint clean: `uv run ruff check src apps tests`.
