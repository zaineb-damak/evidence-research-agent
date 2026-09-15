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
   `require_user` (JWT) from `apps/api/auth.py`. The sole unauthenticated route
   is `POST /auth/token`, which issues the token.
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
src/observability/ OTel tracing + Langfuse handler
src/workflows/    graph assembly (research) + nodes + cost + routing + checkpoint + deps
apps/api/         FastAPI service (JWT-authenticated) + auth + routes_auth + jobs
apps/worker/      Celery worker
apps/web/         React UI (JWT login)
scripts/          create_user, generate_graph_diagram
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
