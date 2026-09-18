import { describe, expect, it } from "vitest";

import {
  buildPlanSteps,
  combineStageStates,
  countCompletedSteps,
  planStepMeta,
  PLAN_STEP_COUNT,
} from "./planSteps";
import { applyProgressEvent, createInitialStreamState } from "./researchEvents";
import type { StageState } from "./researchEvents";
import type { ProgressEvent, StageName } from "../api/types";

const STARTED_AT = "2026-09-18T21:41:00.000Z";
const DONE_AT = "2026-09-18T21:41:03.000Z";

function stage(overrides: Partial<StageState> = {}): StageState {
  return { status: "pending", startedAt: null, doneAt: null, substeps: [], ...overrides };
}

function event(overrides: Partial<ProgressEvent>): ProgressEvent {
  return {
    research_id: "r1",
    event_type: "stage_started",
    stage: null,
    status: "planning",
    message: "",
    detail: {},
    emitted_at: STARTED_AT,
    ...overrides,
  };
}

describe("combineStageStates", () => {
  it("is done only once every constituent stage is done", () => {
    const combined = combineStageStates([
      stage({ status: "done", startedAt: STARTED_AT, doneAt: DONE_AT }),
      stage({ status: "active", startedAt: DONE_AT }),
    ]);

    expect(combined.status).toBe("active");
  });

  it("reports the earliest start and latest finish of its stages", () => {
    const combined = combineStageStates([
      stage({ status: "done", startedAt: STARTED_AT, doneAt: DONE_AT }),
      stage({ status: "done", startedAt: DONE_AT, doneAt: "2026-09-18T21:41:09.000Z" }),
    ]);

    expect(combined).toMatchObject({
      status: "done",
      startedAt: STARTED_AT,
      doneAt: "2026-09-18T21:41:09.000Z",
    });
  });

  it("lets an error win over a done sibling", () => {
    const combined = combineStageStates([
      stage({ status: "done", startedAt: STARTED_AT, doneAt: DONE_AT }),
      stage({ status: "error", startedAt: DONE_AT }),
    ]);

    expect(combined.status).toBe("error");
  });
});

describe("planStepMeta", () => {
  it("shows the elapsed time on a finished step", () => {
    expect(planStepMeta(stage({ status: "done", startedAt: STARTED_AT, doneAt: DONE_AT }))).toBe(
      "done · 3s",
    );
  });

  it("shows the latest substep on the step in flight", () => {
    const state = stage({
      status: "active",
      startedAt: STARTED_AT,
      substeps: [
        { message: "searching web", detail: {}, at: STARTED_AT },
        { message: "12 results", detail: {}, at: DONE_AT },
      ],
    });

    expect(planStepMeta(state)).toBe("12 results");
  });

  it("falls back to a queued label for a step that hasn't started", () => {
    expect(planStepMeta(stage())).toBe("queued");
  });
});

describe("buildPlanSteps", () => {
  it("renders one step per definition and folds score+verify into one", () => {
    const steps = buildPlanSteps(createInitialStreamState());

    expect(steps).toHaveLength(PLAN_STEP_COUNT);
    expect(steps.map((step) => step.key)).toEqual([
      "plan",
      "search",
      "extract",
      "verify",
      "synthesize",
    ]);
  });

  it("counts completed steps from the live stream state", () => {
    let state = createInitialStreamState();
    const finished: StageName[] = ["plan", "search"];
    for (const name of finished) {
      state = applyProgressEvent(
        state,
        event({ event_type: "stage_started", stage: name, status: "planning" }),
      );
      state = applyProgressEvent(
        state,
        event({
          event_type: "stage_completed",
          stage: name,
          status: "searching",
          emitted_at: DONE_AT,
        }),
      );
    }

    expect(countCompletedSteps(buildPlanSteps(state))).toBe(finished.length);
  });

  it("marks every step done for a run that was already completed", () => {
    const state = applyProgressEvent(
      createInitialStreamState(),
      event({ event_type: "snapshot", status: "completed" }),
    );

    expect(countCompletedSteps(buildPlanSteps(state))).toBe(PLAN_STEP_COUNT);
  });
});
