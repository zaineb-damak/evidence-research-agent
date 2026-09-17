// Shared constants — no magic values in components.

import type { ClaimStatus, ResearchStatus, StageName } from "./api/types";

export const API_BASE_PATH = "/api/research";
export const AUTH_TOKEN_PATH = "/auth/token";
export const AUTH_SIGNUP_PATH = "/auth/signup";

// Path segment for the live-progress SSE endpoint (GET /api/research/{id}/events).
export const RESEARCH_EVENTS_PATH_SEGMENT = "/events";

// sessionStorage key for the JWT access token (per-tab, cleared on logout).
export const AUTH_TOKEN_STORAGE_KEY = "research_agent_access_token";

// sessionStorage key for the email the user typed at login/signup. There is
// no backend /me endpoint, so the account menu displays this cached value
// instead of fetching identity from the server (known v1 limitation).
export const AUTH_EMAIL_STORAGE_KEY = "research_agent_account_email";

// Backend minimum password length (apps/api/routes_auth.py::MIN_PASSWORD_LENGTH),
// mirrored here so the signup form validates inline before submitting.
export const MIN_PASSWORD_LENGTH = 8;

export const CLAIM_STATUS_LABELS: Record<ClaimStatus, string> = {
  verified: "Verified",
  partially_supported: "Partially supported",
  conflicting: "Conflicting",
  unsupported: "Unsupported",
  unverified: "Unverified",
};

export const PERCENT_MULTIPLIER = 100;

// The three signal colors defined in styles/tokens.css
// (--verified/--pending/--contradiction). Every status-like value in the app
// (research job status, claim status) maps onto one of these three, rather
// than inventing its own color.
export type StatusTone = "verified" | "pending" | "contradiction";

export const RESEARCH_STATUS_TONE: Record<ResearchStatus, StatusTone> = {
  queued: "pending",
  planning: "pending",
  searching: "pending",
  extracting: "pending",
  resolving: "pending",
  verifying: "pending",
  synthesizing: "pending",
  completed: "verified",
  failed: "contradiction",
};

export const CLAIM_STATUS_TONE: Record<ClaimStatus, StatusTone> = {
  verified: "verified",
  partially_supported: "pending",
  conflicting: "contradiction",
  unsupported: "pending",
  unverified: "pending",
};

// The 6 LangGraph pipeline stages, in graph order (src/models/schemas.py::NodeName).
export const STAGE_ORDER: StageName[] = [
  "plan",
  "search",
  "extract",
  "score",
  "verify",
  "synthesize",
];
