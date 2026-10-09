// Default runtime configuration, used by the Vite dev server.
//
// In the container image this file is never read: nginx answers /config.js
// directly from the APP_API_BASE_URL environment variable (see
// infra/docker/nginx-default.conf.template), which is what lets one built image
// serve every environment without a writable filesystem.
//
// Empty apiBaseUrl means same-origin: the Vite proxy forwards /api and /auth to
// the API in dev, and nginx does the same in the container.
window.__APP_CONFIG__ = { apiBaseUrl: "" };
