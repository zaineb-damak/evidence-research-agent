// Typed API client. Every request carries the caller's JWT bearer token
// (apps/api/auth.py), obtained via the login flow (see api/auth.ts). A 401
// clears the stored token so the app returns the user to the login screen.

import { API_BASE_PATH } from "../constants";
import { clearToken, getToken } from "./auth";
import type {
  Claim,
  CreateResearchResponse,
  EvidenceGraph,
  ReportResponse,
  ResearchDepth,
  ResearchJobListItem,
  ResearchJobSummary,
  Source,
  SourceType,
} from "./types";

const AUTHORIZATION_HEADER = "Authorization";
const CONTENT_TYPE_HEADER = "Content-Type";
const JSON_CONTENT_TYPE = "application/json";
const UNAUTHORIZED_STATUS = 401;

export class UnauthorizedError extends Error {}

function authHeaders(): Record<string, string> {
  const headers: Record<string, string> = {
    [CONTENT_TYPE_HEADER]: JSON_CONTENT_TYPE,
  };
  const token = getToken();
  if (token !== null) {
    headers[AUTHORIZATION_HEADER] = `Bearer ${token}`;
  }
  return headers;
}

function raiseForStatus(response: Response, path: string): void {
  if (response.status === UNAUTHORIZED_STATUS) {
    clearToken();
    throw new UnauthorizedError(`Unauthorized: ${path}`);
  }
  if (!response.ok) {
    throw new Error(`Request failed (${response.status}): ${path}`);
  }
}

async function getJson<ResponseType>(path: string): Promise<ResponseType> {
  const response = await fetch(path, { headers: authHeaders() });
  raiseForStatus(response, path);
  return (await response.json()) as ResponseType;
}

export interface CreateResearchInput {
  question: string;
  depth: ResearchDepth;
  sourceTypes: SourceType[];
}

export async function createResearch(
  input: CreateResearchInput,
): Promise<CreateResearchResponse> {
  const response = await fetch(API_BASE_PATH, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify({
      question: input.question,
      depth: input.depth,
      source_types: input.sourceTypes,
    }),
  });
  raiseForStatus(response, API_BASE_PATH);
  return (await response.json()) as CreateResearchResponse;
}

export function getJobSummary(researchId: string): Promise<ResearchJobSummary> {
  return getJson<ResearchJobSummary>(`${API_BASE_PATH}/${researchId}`);
}

export function getClaims(researchId: string): Promise<Claim[]> {
  return getJson<Claim[]>(`${API_BASE_PATH}/${researchId}/claims`);
}

export function getSources(researchId: string): Promise<Source[]> {
  return getJson<Source[]>(`${API_BASE_PATH}/${researchId}/sources`);
}

export function getGraph(researchId: string): Promise<EvidenceGraph> {
  return getJson<EvidenceGraph>(`${API_BASE_PATH}/${researchId}/graph`);
}

export function getReport(researchId: string): Promise<ReportResponse> {
  return getJson<ReportResponse>(`${API_BASE_PATH}/${researchId}/report`);
}

// GET /api/research — the caller's own research jobs, newest first
// (backs the history sidebar; see hooks/useSessions.ts).
export function getSessions(): Promise<ResearchJobListItem[]> {
  return getJson<ResearchJobListItem[]>(API_BASE_PATH);
}
