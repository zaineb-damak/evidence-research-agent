// Runtime configuration, injected by the container at startup.
//
// The built SPA is a static bundle, so baking an API URL in at `vite build`
// time would mean one image per environment. Instead /config.js is supplied at
// runtime — by public/config.js in dev, and by nginx from the environment in
// the container (infra/docker/nginx-default.conf.template) — which keeps a
// single image promotable from staging to production.
//
// The default is same-origin: nginx serves the bundle and proxies /api and
// /auth to the API service, so requests stay relative and no CORS is involved.
// Setting apiBaseUrl is for the case where the API lives on another host.

export interface RuntimeConfig {
  apiBaseUrl?: string;
}

declare global {
  interface Window {
    __APP_CONFIG__?: RuntimeConfig;
  }
}

const SAME_ORIGIN = "";
const TRAILING_SLASHES = /\/+$/;

function readApiBaseUrl(): string {
  const configured = window.__APP_CONFIG__?.apiBaseUrl ?? SAME_ORIGIN;
  // A trailing slash would turn "/api/research" into "//api/research".
  return configured.replace(TRAILING_SLASHES, SAME_ORIGIN);
}

export const API_ORIGIN = readApiBaseUrl();
