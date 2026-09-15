// Pure formatting helpers, kept out of components.

import {
  CONFIDENCE_BAR_SEGMENTS,
  PERCENT_MULTIPLIER,
} from "../constants";

export function toPercent(value: number): number {
  return Math.round(value * PERCENT_MULTIPLIER);
}

export function confidenceBar(value: number): string {
  const filledSegments = Math.round(value * CONFIDENCE_BAR_SEGMENTS);
  const emptySegments = CONFIDENCE_BAR_SEGMENTS - filledSegments;
  return "█".repeat(filledSegments) + "░".repeat(emptySegments);
}
