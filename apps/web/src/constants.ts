// Shared constants — no magic values in components.

import type { ClaimStatus } from "./api/types";

export const API_BASE_PATH = "/api/research";
export const AUTH_TOKEN_PATH = "/auth/token";

// sessionStorage key for the JWT access token (per-tab, cleared on logout).
export const AUTH_TOKEN_STORAGE_KEY = "research_agent_access_token";

// How often the progress view polls a running job.
export const JOB_POLL_INTERVAL_MS = 1500;

// Human-readable, ordered pipeline steps shown in the progress view.
export const PIPELINE_STEPS: { status: string; label: string }[] = [
  { status: "planning", label: "Understanding research question" },
  { status: "searching", label: "Searching sources" },
  { status: "extracting", label: "Extracting evidence" },
  { status: "verifying", label: "Verifying claims" },
  { status: "synthesizing", label: "Generating final report" },
  { status: "completed", label: "Done" },
];

export const CLAIM_STATUS_LABELS: Record<ClaimStatus, string> = {
  verified: "Verified",
  partially_supported: "Partially supported",
  conflicting: "Conflicting",
  unsupported: "Unsupported",
  unverified: "Unverified",
};

export const CLAIM_STATUS_COLORS: Record<ClaimStatus, string> = {
  verified: "#1a7f37",
  partially_supported: "#9a6700",
  conflicting: "#cf222e",
  unsupported: "#57606a",
  unverified: "#57606a",
};

export const CONFIDENCE_BAR_SEGMENTS = 20;
export const PERCENT_MULTIPLIER = 100;
