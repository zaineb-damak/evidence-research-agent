// Shared constants — no magic values in components.

import type {
  ClaimStatus,
  ResearchDepth,
  ResearchStatus,
  SourceType,
  StageName,
} from "./api/types";
import { API_ORIGIN } from "./runtimeConfig";

// API_ORIGIN is empty in the default same-origin deployment, so these stay the
// relative paths the dev-server proxy and the nginx image both expect.
export const API_BASE_PATH = `${API_ORIGIN}/api/research`;
export const AUTH_TOKEN_PATH = `${API_ORIGIN}/auth/token`;
export const AUTH_SIGNUP_PATH = `${API_ORIGIN}/auth/signup`;

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

// Product name and copy shared across the shell and the auth screens
// (design_handoff_research_agent/README.md).
export const BRAND_NAME = "Lantern";

export const HISTORY_SEARCH_PLACEHOLDER = "Search history";

// lucide-react's default stroke is 2px, which reads heavy next to this
// design's hairlines and 400/500 type.
export const ICON_STROKE_WIDTH = 1.75;

// Depth: the design's three-segment control. "Balanced" is the backend's
// `normal` (src/models/schemas.py::ResearchDepth).
export interface DepthOption {
  value: ResearchDepth;
  label: string;
}

export const DEPTH_OPTIONS: DepthOption[] = [
  { value: "fast", label: "Fast" },
  { value: "normal", label: "Balanced" },
  { value: "deep", label: "Deep" },
];

export const DEFAULT_DEPTH: ResearchDepth = "normal";

export const DEPTH_LABELS: Record<ResearchDepth, string> = {
  fast: "Fast",
  normal: "Balanced",
  deep: "Deep",
};

// Source chips, in the design's order. Labels are the design's; values are
// the backend's SourceType members.
export interface SourceTypeOption {
  value: SourceType;
  label: string;
}

export const SOURCE_TYPE_OPTIONS: SourceTypeOption[] = [
  { value: "web", label: "Web" },
  { value: "documentation", label: "Docs" },
  { value: "paper", label: "Papers" },
  { value: "arxiv", label: "arXiv" },
  { value: "github", label: "GitHub" },
  { value: "reddit", label: "Reddit" },
];

export const DEFAULT_SOURCE_TYPES: SourceType[] = ["web", "documentation", "paper"];

// Prefill-and-run chips under the composer.
export const SUGGESTED_QUESTIONS: string[] = [
  "Which open model is cheapest per resolved ticket?",
  "Summarize the 2026 EU AI Act deployer duties",
  "Best RAG eval harness for support transcripts",
];

// How many sources the report's "Key sources" grid shows, highest quality
// score first.
export const KEY_SOURCE_COUNT = 4;

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
