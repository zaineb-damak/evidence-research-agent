import { describe, expect, it } from "vitest";

import { STAGE_ORDER } from "../constants";
import { applyProgressEvent, createInitialStreamState } from "./researchEvents";
import type { ResearchStreamState } from "./researchEvents";
import type { ProgressEvent, StageName } from "../api/types";

const RESEARCH_ID = "research_123";

function stageStarted(stage: StageName, status: ProgressEvent["status"]): ProgressEvent {
  return {
    research_id: RESEARCH_ID,
    event_type: "stage_started",
    stage,
    status,
    message: `Started ${stage}`,
    detail: {},
    emitted_at: `2026-01-01T00:00:0${STAGE_ORDER.indexOf(stage)}.000Z`,
  };
}

function stageCompleted(
  stage: StageName,
  status: ProgressEvent["status"],
  detail: Record<string, unknown> = {},
): ProgressEvent {
  return {
    research_id: RESEARCH_ID,
    event_type: "stage_completed",
    stage,
    status,
    message: `Completed ${stage}`,
    detail,
    emitted_at: `2026-01-01T00:00:1${STAGE_ORDER.indexOf(stage)}.000Z`,
  };
}

function substep(
  stage: StageName,
  status: ProgressEvent["status"],
  detail: Record<string, unknown>,
): ProgressEvent {
  return {
    research_id: RESEARCH_ID,
    event_type: "substep",
    stage,
    status,
    message: `Progress on ${stage}`,
    detail,
    emitted_at: "2026-01-01T00:00:05.500Z",
  };
}

function reduceAll(events: ProgressEvent[]): ResearchStreamState {
  return events.reduce(applyProgressEvent, createInitialStreamState());
}

describe("applyProgressEvent", () => {
  it("walks a normal full sequence to every stage done and overall completed", () => {
    const events: ProgressEvent[] = [
      stageStarted("plan", "planning"),
      stageCompleted("plan", "planning", { research_tasks_count: 3 }),
      stageStarted("search", "searching"),
      substep("search", "searching", { sources_found: 1 }),
      substep("search", "searching", { sources_found: 2 }),
      stageCompleted("search", "searching", { sources_count: 2 }),
      stageStarted("extract", "extracting"),
      stageCompleted("extract", "extracting", { claims_count: 5 }),
      stageStarted("score", "resolving"),
      stageCompleted("score", "resolving"),
      stageStarted("verify", "verifying"),
      stageCompleted("verify", "verifying", { contradictions_count: 0 }),
      stageStarted("synthesize", "synthesizing"),
      stageCompleted("synthesize", "completed", { cost_usd: 0.42 }),
      {
        research_id: RESEARCH_ID,
        event_type: "done",
        stage: null,
        status: "completed",
        message: "Research complete",
        detail: {},
        emitted_at: "2026-01-01T00:00:20.000Z",
      },
    ];

    const finalState = reduceAll(events);

    expect(finalState.overallStatus).toBe("completed");
    for (const stage of STAGE_ORDER) {
      expect(finalState.stages[stage].status).toBe("done");
    }
    expect(finalState.stages.search.substeps).toHaveLength(2);
    expect(finalState.counts.sources_count).toBe(2);
    expect(finalState.counts.claims_count).toBe(5);
    expect(finalState.cost).toBe(0.42);
  });

  it("marks synthesize done on the terminal DONE event even without its own stage_completed", () => {
    const events: ProgressEvent[] = [
      stageStarted("plan", "planning"),
      stageCompleted("plan", "planning"),
      stageStarted("search", "searching"),
      stageCompleted("search", "searching"),
      stageStarted("extract", "extracting"),
      stageCompleted("extract", "extracting"),
      stageStarted("score", "resolving"),
      stageCompleted("score", "resolving"),
      stageStarted("verify", "verifying"),
      stageCompleted("verify", "verifying"),
      // synthesize only ever gets STAGE_STARTED — no STAGE_COMPLETED.
      stageStarted("synthesize", "synthesizing"),
      {
        research_id: RESEARCH_ID,
        event_type: "done",
        stage: null,
        status: "completed",
        message: "Research complete",
        detail: {},
        emitted_at: "2026-01-01T00:00:20.000Z",
      },
    ];

    const finalState = reduceAll(events);

    expect(finalState.stages.synthesize.status).toBe("done");
    expect(finalState.overallStatus).toBe("completed");
    for (const stage of STAGE_ORDER) {
      expect(finalState.stages[stage].status).toBe("done");
    }
  });

  it("halts further progress after an error event", () => {
    const events: ProgressEvent[] = [
      stageStarted("plan", "planning"),
      stageCompleted("plan", "planning"),
      stageStarted("search", "searching"),
      substep("search", "searching", { sources_found: 1 }),
      {
        research_id: RESEARCH_ID,
        event_type: "error",
        stage: null,
        status: "failed",
        message: "Connector timed out",
        detail: {},
        emitted_at: "2026-01-01T00:00:09.000Z",
      },
      // A stray late event after the terminal error must be ignored.
      stageStarted("extract", "extracting"),
    ];

    const finalState = reduceAll(events);

    expect(finalState.overallStatus).toBe("failed");
    expect(finalState.error).toBe("Connector timed out");
    expect(finalState.stages.search.status).toBe("error");
    expect(finalState.stages.plan.status).toBe("done");
    // The stray post-error event must not have been applied.
    expect(finalState.stages.extract.status).toBe("pending");
  });
});
