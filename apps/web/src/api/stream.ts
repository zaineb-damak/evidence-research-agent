// SSE transport for live research progress. This is the only file that knows
// about the fetch/auth mechanics of the stream — `GET /api/research/{id}/events`
// requires the same `Authorization: Bearer` header as every other request, so
// (per the plan) we use `fetch` + a manual reader rather than the native
// `EventSource`, which cannot send custom headers.

import { API_BASE_PATH, RESEARCH_EVENTS_PATH_SEGMENT } from "../constants";
import { getToken } from "./auth";

const AUTHORIZATION_HEADER = "Authorization";

export function buildResearchEventsUrl(researchId: string): string {
  return `${API_BASE_PATH}/${researchId}${RESEARCH_EVENTS_PATH_SEGMENT}`;
}

// Opens the SSE endpoint and yields raw decoded text chunks as they arrive.
// Callers (hooks/useResearchStream.ts) feed each chunk into lib/sse.ts's
// parser. Throws if the connection cannot be opened; ends normally (return)
// when the server closes the stream.
export async function* streamResearchEvents(
  researchId: string,
  signal: AbortSignal,
): AsyncGenerator<string> {
  const headers: Record<string, string> = {};
  const token = getToken();
  if (token !== null) {
    headers[AUTHORIZATION_HEADER] = `Bearer ${token}`;
  }

  const url = buildResearchEventsUrl(researchId);
  const response = await fetch(url, { headers, signal });
  if (!response.ok || response.body === null) {
    throw new Error(`Stream request failed (${response.status}): ${url}`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) {
        return;
      }
      yield decoder.decode(value, { stream: true });
    }
  } finally {
    reader.releaseLock();
  }
}
