#!/usr/bin/env bash
#
# Deploy the chart to one environment. Shared by the staging and production
# jobs in release.yml so the two paths cannot drift apart.
#
# MIGRATION SAFETY
# ----------------
# The chart runs `alembic upgrade head` as a pre-upgrade Helm hook Job, so the
# schema is migrated *before* the new pods roll. `--atomic` rolls the release
# back if the rollout fails — but it cannot un-run a migration, and Helm will
# not re-run the hook backwards.
#
# That makes one invariant load-bearing: every migration must be backward
# compatible with the previous release (expand/contract). Add a column,
# backfill and start writing it in one release; stop reading the old column in
# the next; drop it in a third. A migration that renames or drops in a single
# step turns an automatic rollback into an outage.

set -euo pipefail

: "${KUBE_CONFIG:?base64-encoded kubeconfig for the target cluster}"
: "${RELEASE_NAME:?}"
: "${NAMESPACE:?}"
: "${VALUES_FILE:?}"
: "${IMAGE_PREFIX:?}"
: "${IMAGE_TAG:?}"

CHART_DIR="infra/k8s/chart"
ROLLOUT_TIMEOUT="10m"
# values-prod.yaml ships unusable placeholders for every managed endpoint, so
# that forgetting to supply one is a loud failure rather than a release that
# cannot reach its database.
PLACEHOLDER="REPLACE_ME"

kubeconfig_path="$(mktemp)"
# The kubeconfig holds cluster credentials; never leave it on the runner disk.
trap 'rm -f "${kubeconfig_path}"' EXIT
printf '%s' "${KUBE_CONFIG}" | base64 --decode >"${kubeconfig_path}"
chmod 600 "${kubeconfig_path}"
export KUBECONFIG="${kubeconfig_path}"

# GHCR paths must be lowercase, and GitHub preserves the case of owner names.
image_prefix="${IMAGE_PREFIX,,}"

helm_args=(
  "${RELEASE_NAME}" "${CHART_DIR}"
  --namespace "${NAMESPACE}"
  --values "${VALUES_FILE}"
  --set "image.tag=${IMAGE_TAG}"
  --set "image.api.repository=${image_prefix}-api"
  --set "image.worker.repository=${image_prefix}-worker"
  --set "image.web.repository=${image_prefix}-web"
)

# Render first and refuse to ship an unconfigured placeholder. Doing this before
# the upgrade matters: once the pre-upgrade migration hook has run, a failed
# release is no longer a clean no-op.
if helm template "${helm_args[@]}" | grep --quiet "${PLACEHOLDER}"; then
  echo "refusing to deploy: ${PLACEHOLDER} remains in the rendered release." >&2
  echo "supply the real endpoints with --set-string from your secret store." >&2
  exit 1
fi

helm upgrade --install "${helm_args[@]}" \
  --create-namespace \
  --wait \
  --atomic \
  --timeout "${ROLLOUT_TIMEOUT}"

helm status "${RELEASE_NAME}" --namespace "${NAMESPACE}"
