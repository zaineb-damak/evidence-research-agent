// Pure formatting helpers, kept out of components.

import { PERCENT_MULTIPLIER } from "../constants";

export function toPercent(value: number): number {
  return Math.round(value * PERCENT_MULTIPLIER);
}

const USD_CURRENCY_FORMAT_OPTIONS: Intl.NumberFormatOptions = {
  style: "currency",
  currency: "USD",
  minimumFractionDigits: 2,
  maximumFractionDigits: 4,
};

export function formatUsd(amount: number): string {
  return new Intl.NumberFormat(undefined, USD_CURRENCY_FORMAT_OPTIONS).format(amount);
}

const MILLISECONDS_PER_SECOND_FOR_ELAPSED = 1000;
const SECONDS_PER_MINUTE_FOR_ELAPSED = 60;

// A short elapsed-time label for a completed stage row, e.g. "3s" or "2m 14s".
export function formatElapsedDuration(startedAt: string, doneAt: string): string {
  const elapsedMs = Math.max(
    0,
    new Date(doneAt).getTime() - new Date(startedAt).getTime(),
  );
  const totalSeconds = Math.round(elapsedMs / MILLISECONDS_PER_SECOND_FOR_ELAPSED);
  const minutes = Math.floor(totalSeconds / SECONDS_PER_MINUTE_FOR_ELAPSED);
  const seconds = totalSeconds % SECONDS_PER_MINUTE_FOR_ELAPSED;
  if (minutes === 0) {
    return `${seconds}s`;
  }
  return `${minutes}m ${seconds}s`;
}

const MILLISECONDS_PER_SECOND = 1000;
const SECONDS_PER_MINUTE = 60;
const MINUTES_PER_HOUR = 60;

const MILLISECONDS_PER_MINUTE = MILLISECONDS_PER_SECOND * SECONDS_PER_MINUTE;
const MILLISECONDS_PER_HOUR = MILLISECONDS_PER_MINUTE * MINUTES_PER_HOUR;

const JUST_NOW_THRESHOLD_MS = MILLISECONDS_PER_MINUTE;

const RELATIVE_DATE_FORMAT_OPTIONS: Intl.DateTimeFormatOptions = {
  month: "short",
  day: "numeric",
};

function startOfLocalDay(date: Date): Date {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate());
}

// Whether `date` falls on the same local calendar day as `now` (defaults to
// the current moment) — used to group session-history items into
// "Today"/"Earlier" sections.
export function isToday(date: Date, now: Date = new Date()): boolean {
  return startOfLocalDay(date).getTime() === startOfLocalDay(now).getTime();
}

// A short, human-readable relative timestamp: "Just now", "14m ago",
// "3h ago", "Yesterday", or a short date ("Sep 12") for anything older.
export function formatRelativeTime(date: Date, now: Date = new Date()): string {
  const elapsedMs = now.getTime() - date.getTime();

  if (elapsedMs < JUST_NOW_THRESHOLD_MS) {
    return "Just now";
  }
  if (elapsedMs < MILLISECONDS_PER_HOUR) {
    const minutes = Math.floor(elapsedMs / MILLISECONDS_PER_MINUTE);
    return `${minutes}m ago`;
  }
  if (isToday(date, now)) {
    const hours = Math.floor(elapsedMs / MILLISECONDS_PER_HOUR);
    return `${hours}h ago`;
  }
  const yesterday = new Date(now.getTime());
  yesterday.setDate(yesterday.getDate() - 1);
  if (isToday(date, yesterday)) {
    return "Yesterday";
  }
  return date.toLocaleDateString(undefined, RELATIVE_DATE_FORMAT_OPTIONS);
}
