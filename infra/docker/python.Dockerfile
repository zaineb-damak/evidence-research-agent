# syntax=docker/dockerfile:1.9
#
# One Dockerfile, two published images: `api` and `worker`. They share every
# layer up to `runtime`, so the registry stores the dependency set once and a
# node that has pulled one pulls almost nothing for the other.
#
# Build from the repository root:
#   docker build -f infra/docker/python.Dockerfile --target api    -t research-agent-api .
#   docker build -f infra/docker/python.Dockerfile --target worker -t research-agent-worker .
#
# Database migrations reuse the `api` image with a different command, so there
# is no third image to build, scan and promote.

ARG PYTHON_VERSION=3.12
ARG UV_VERSION=0.5.11
ARG DEBIAN_RELEASE=bookworm

# --- builder -----------------------------------------------------------------
# Resolves dependencies from uv.lock into a self-contained virtualenv.

FROM ghcr.io/astral-sh/uv:${UV_VERSION}-python${PYTHON_VERSION}-${DEBIAN_RELEASE}-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

# Only needed if a dependency has no wheel for the target architecture; none of
# this reaches the runtime image.
RUN apt-get update \
 && apt-get install --yes --no-install-recommends build-essential \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Dependencies are installed before the source is copied, so editing a Python
# file does not invalidate the (slow, large) dependency layer.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    uv sync --frozen --no-dev --no-install-project

COPY pyproject.toml uv.lock README.md ./
COPY src ./src
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# --- runtime -----------------------------------------------------------------
# The common base for both images: interpreter, virtualenv, source, non-root user.

FROM python:${PYTHON_VERSION}-slim-${DEBIAN_RELEASE} AS runtime

ARG RELEASE_VERSION=dev
ARG APP_UID=10001
ARG APP_GID=10001

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONFAULTHANDLER=1 \
    PATH="/app/.venv/bin:${PATH}" \
    RELEASE_VERSION=${RELEASE_VERSION} \
    LOG_FORMAT=json

# A fixed high uid/gid so the Kubernetes securityContext can pin the same values
# and the filesystem stays readable when the root filesystem is mounted read-only.
RUN groupadd --system --gid ${APP_GID} app \
 && useradd --system --uid ${APP_UID} --gid app --home-dir /app --shell /usr/sbin/nologin app

WORKDIR /app

COPY --from=builder --chown=${APP_UID}:${APP_GID} /app/.venv /app/.venv
COPY --chown=${APP_UID}:${APP_GID} pyproject.toml alembic.ini README.md ./
COPY --chown=${APP_UID}:${APP_GID} src ./src
COPY --chown=${APP_UID}:${APP_GID} apps ./apps
COPY --chown=${APP_UID}:${APP_GID} scripts ./scripts

# Numeric, so a Kubernetes `runAsNonRoot` admission check can verify the user
# without resolving names inside the image.
USER ${APP_UID}:${APP_GID}

# --- api ---------------------------------------------------------------------

FROM runtime AS api

ARG API_PORT=8000
ENV API_PORT=${API_PORT}
EXPOSE ${API_PORT}

# One uvicorn process per container: replicas are the unit of scale in
# Kubernetes, and a single process keeps the Prometheus registry accurate.
# --proxy-headers so client IPs survive the ingress hop.
CMD ["sh", "-c", "exec uvicorn apps.api.main:app --host 0.0.0.0 --port ${API_PORT} --proxy-headers --forwarded-allow-ips='*'"]

# Compose-only: Kubernetes uses the probes declared in the Helm chart instead.
# Python rather than curl, which the slim image does not ship.
HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=3 \
  CMD ["python", "-c", "import os,urllib.request;urllib.request.urlopen('http://127.0.0.1:'+os.environ['API_PORT']+'/health/live').read()"]

# --- worker ------------------------------------------------------------------

FROM runtime AS worker

ARG WORKER_METRICS_PORT=9100
ARG WORKER_CONCURRENCY=8
ENV WORKER_METRICS_PORT=${WORKER_METRICS_PORT} \
    WORKER_CONCURRENCY=${WORKER_CONCURRENCY}
EXPOSE ${WORKER_METRICS_PORT}

# The thread pool, not prefork: the pipeline is I/O-bound (LLM and HTTP calls),
# and keeping tasks in the main process is what lets that process serve accurate
# /metrics (see apps/worker/celery_app.py).
CMD ["sh", "-c", "exec celery -A apps.worker.celery_app worker --loglevel=INFO --pool=threads --concurrency=${WORKER_CONCURRENCY}"]

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD ["sh", "-c", "celery -A apps.worker.celery_app inspect ping --destination \"celery@$HOSTNAME\""]
