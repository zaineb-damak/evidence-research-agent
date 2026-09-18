// Pure helpers behind the report's "Key sources" grid.

import { KEY_SOURCE_COUNT } from "../constants";
import type { Source } from "../api/types";

// Highest-quality sources first — the grid shows a handful, not the full
// source list (that lives in the report's Sources section and the evidence
// explorer).
export function topSourcesByQuality(
  sources: Source[],
  limit: number = KEY_SOURCE_COUNT,
): Source[] {
  return [...sources]
    .sort((left, right) => right.quality.score - left.quality.score)
    .slice(0, limit);
}

// The host line on a source card: the backend's domain when it has one,
// otherwise the URL's host, falling back to the raw URL if it won't parse.
export function sourceHost(source: Source): string {
  if (source.domain !== null && source.domain !== "") {
    return source.domain;
  }
  try {
    return new URL(source.url).host;
  } catch {
    return source.url;
  }
}

export function sourceTitle(source: Source): string {
  return source.title !== null && source.title !== "" ? source.title : sourceHost(source);
}
