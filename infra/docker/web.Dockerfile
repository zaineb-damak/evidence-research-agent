# syntax=docker/dockerfile:1.9
#
# The React SPA, built once and served by nginx.
#
# Build from the repository root:
#   docker build -f infra/docker/web.Dockerfile -t research-agent-web .
#
# The bundle carries no environment-specific values: the API location is read at
# runtime from /config.js (see apps/web/src/runtimeConfig.ts), so the same image
# is promoted from staging to production unchanged.

ARG NODE_VERSION=22
ARG NGINX_VERSION=1.27

# --- builder -----------------------------------------------------------------

FROM node:${NODE_VERSION}-alpine AS builder

WORKDIR /app

# `npm ci` from the lockfile only — reproducible, and cached until the lockfile
# changes rather than on every source edit.
COPY apps/web/package.json apps/web/package-lock.json ./
RUN --mount=type=cache,target=/root/.npm npm ci

COPY apps/web/ ./
RUN npm run build

# --- runtime -----------------------------------------------------------------
# nginx-unprivileged already runs as a non-root user and listens on a high port,
# which is what a hardened Kubernetes securityContext requires.

FROM nginxinc/nginx-unprivileged:${NGINX_VERSION}-alpine AS runtime

ARG RELEASE_VERSION=dev
ARG WEB_PORT=8080

ENV RELEASE_VERSION=${RELEASE_VERSION}
ENV WEB_PORT=${WEB_PORT}

# Where nginx forwards /api and /auth — the API Service inside the cluster.
ENV APP_API_UPSTREAM=http://api:8000

# The API origin the browser should call, served as /config.js. Empty means
# same-origin, i.e. through the proxy below: the default, and the only setup
# that needs no CORS. nginx returns it from the config rather than writing a
# file, so the container runs with a read-only root filesystem.
ENV APP_API_BASE_URL=""

# nginx's own entrypoint runs envsubst over /etc/nginx/templates/*.template.
# The filter stops it from mangling nginx variables such as $uri and $host.
ENV NGINX_ENVSUBST_FILTER="^(APP_|WEB_PORT)"

# The directories are created explicitly, as root, before the config lands in
# them: letting COPY --chmod create them applies that file mode to the parent
# directory too, and a 0644 directory cannot be traversed by the nginx user —
# the template is then silently skipped and nginx serves its stock config.
USER root
RUN mkdir --parents /etc/nginx/templates /etc/nginx/snippets \
 && chmod 0755 /etc/nginx/templates /etc/nginx/snippets

COPY --chmod=0644 infra/docker/nginx-default.conf.template \
     /etc/nginx/templates/default.conf.template
COPY --chmod=0644 infra/docker/nginx-security-headers.conf \
     /etc/nginx/snippets/security-headers.conf

COPY --from=builder /app/dist /usr/share/nginx/html

# Numeric (nginx-unprivileged's own uid), so a Kubernetes `runAsNonRoot`
# admission check can verify it without resolving names inside the image.
USER 101:101

EXPOSE ${WEB_PORT}

HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
  CMD ["sh", "-c", "wget --quiet --spider \"http://127.0.0.1:${WEB_PORT}/healthz\" || exit 1"]
