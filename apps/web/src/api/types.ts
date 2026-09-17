// TypeScript interfaces mirroring the backend Pydantic schemas
// (src/models/schemas.py). Kept in sync by hand; the shapes are intentionally
// the same so the Evidence Explorer renders nested claim/evidence/source data.

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export type ResearchDepth = "fast" | "normal" | "deep";

export type SourceType =
  | "web"
  | "paper"
  | "documentation"
  | "github"
  | "arxiv"
  | "youtube"
  | "reddit"
  | "api";

export type ResearchStatus =
  | "queued"
  | "planning"
  | "searching"
  | "extracting"
  | "resolving"
  | "verifying"
  | "synthesizing"
  | "completed"
  | "failed";

export type ClaimStatus =
  | "verified"
  | "partially_supported"
  | "conflicting"
  | "unsupported"
  | "unverified";

export interface CostMeter {
  tokens_in: number;
  tokens_out: number;
  usd: number;
  latency_ms: number;
}

export interface ResearchJobSummary {
  research_id: string;
  question: string;
  status: ResearchStatus;
  error: string | null;
  counts: {
    sources: number;
    passages: number;
    claims: number;
    contradictions: number;
  };
  cost: CostMeter;
}

export interface ConfidenceBreakdown {
  source_quality: number;
  evidence_strength: number;
  source_agreement: number;
  extraction_confidence: number;
  total: number;
}

export interface Claim {
  id: string;
  text: string;
  subject_entity_id: string | null;
  status: ClaimStatus;
  confidence: number;
  confidence_breakdown: ConfidenceBreakdown;
  evidence_ids: string[];
}

export interface SourceQuality {
  authority: number;
  recency: number;
  relevance: number;
  primary_source_bonus: number;
  corroboration: number;
  score: number;
}

export interface Source {
  id: string;
  url: string;
  title: string | null;
  domain: string | null;
  source_type: SourceType;
  quality: SourceQuality;
}

export interface GraphNode {
  label: string;
  ref_id: string;
  props: Record<string, unknown>;
}

export interface GraphEdge {
  src: string;
  rel: string;
  dst: string;
  meta?: Record<string, unknown>;
}

export interface EvidenceGraph {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface ReportResponse {
  research_id: string;
  status: ResearchStatus;
  report: string;
}

export interface CreateResearchResponse {
  research_id: string;
  status: ResearchStatus;
}

// Lightweight per-job projection for the session-history sidebar
// (GET /api/research). Mirrors src/models/schemas.py::ResearchJobListItem —
// distinct from ResearchJobSummary, which is the single-job detail shape.
export interface ResearchJobListItem {
  research_id: string;
  question: string;
  status: ResearchStatus;
  depth: ResearchDepth;
  error: string | null;
  created_at: string;
  updated_at: string;
}

// The LangGraph node identifiers for the research pipeline graph. Mirrors
// src/models/schemas.py::NodeName exactly — these are the `stage` values on a
// ProgressEvent below.
export type StageName = "plan" | "search" | "extract" | "score" | "verify" | "synthesize";

// Mirrors src/models/progress.py::ProgressEventType.
export type ProgressEventType =
  | "snapshot"
  | "stage_started"
  | "stage_completed"
  | "substep"
  | "done"
  | "error";

// One update in a research job's live-progress stream
// (GET /api/research/{id}/events, SSE). Mirrors src/models/progress.py::ProgressEvent.
export interface ProgressEvent {
  research_id: string;
  event_type: ProgressEventType;
  stage: StageName | null;
  status: ResearchStatus;
  message: string;
  detail: Record<string, unknown>;
  emitted_at: string;
}
