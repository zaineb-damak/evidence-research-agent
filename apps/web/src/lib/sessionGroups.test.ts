import { describe, expect, it } from "vitest";

import type { ResearchJobListItem } from "../api/types";
import {
  filterSessions,
  groupSessionsByRecency,
  SESSION_GROUP_LABEL_OLDER,
  SESSION_GROUP_LABEL_RECENT,
  SESSION_GROUP_LABEL_TODAY,
} from "./sessionGroups";

const NOW = new Date("2026-09-18T21:41:00");

function session(researchId: string, question: string, createdAt: Date): ResearchJobListItem {
  return {
    research_id: researchId,
    question,
    status: "completed",
    depth: "normal",
    error: null,
    created_at: createdAt.toISOString(),
    updated_at: createdAt.toISOString(),
  };
}

function daysBefore(days: number): Date {
  const date = new Date(NOW);
  date.setDate(date.getDate() - days);
  return date;
}

describe("filterSessions", () => {
  const sessions = [
    session("a", "Compare Qwen, Llama and Mistral", NOW),
    session("b", "Vector DB latency at 50M vectors", NOW),
  ];

  it("returns everything for a blank query", () => {
    expect(filterSessions(sessions, "   ")).toHaveLength(2);
  });

  it("matches the question case-insensitively", () => {
    expect(filterSessions(sessions, "MISTRAL").map((item) => item.research_id)).toEqual(["a"]);
  });

  it("returns nothing when no question matches", () => {
    expect(filterSessions(sessions, "kubernetes")).toEqual([]);
  });
});

describe("groupSessionsByRecency", () => {
  it("splits runs into today, the previous 7 days, and older", () => {
    const groups = groupSessionsByRecency(
      [
        session("today", "Today's run", NOW),
        session("recent", "Three days ago", daysBefore(3)),
        session("old", "Two weeks ago", daysBefore(14)),
      ],
      NOW,
    );

    expect(groups.map((group) => group.label)).toEqual([
      SESSION_GROUP_LABEL_TODAY,
      SESSION_GROUP_LABEL_RECENT,
      SESSION_GROUP_LABEL_OLDER,
    ]);
    expect(groups[1].items.map((item) => item.research_id)).toEqual(["recent"]);
  });

  it("omits empty groups and keeps the incoming order within a group", () => {
    const groups = groupSessionsByRecency(
      [session("first", "First", NOW), session("second", "Second", NOW)],
      NOW,
    );

    expect(groups).toHaveLength(1);
    expect(groups[0].label).toBe(SESSION_GROUP_LABEL_TODAY);
    expect(groups[0].items.map((item) => item.research_id)).toEqual(["first", "second"]);
  });

  it("counts a run exactly 7 days old as older, not recent", () => {
    const groups = groupSessionsByRecency([session("edge", "Edge", daysBefore(7))], NOW);

    expect(groups[0].label).toBe(SESSION_GROUP_LABEL_OLDER);
  });
});
