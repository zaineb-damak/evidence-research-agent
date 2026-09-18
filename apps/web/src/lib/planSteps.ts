// Pure mapping from the live stream's per-stage state to the five plan steps
// the research plan card renders. Kept out of the component so the
// combination rules are testable on their own (CLAUDE.md rule 6).
//
// The backend has six pipeline stages (src/models/schemas.py::NodeName);
// `score` and `verify` are shown as one step — from the reader's side both
// operate on the already-extracted claims (confidence scoring, then
// contradiction resolution) with no separate visible output in between.

import type { StageName } from "../api/types";
import type { ResearchStreamState, StageState, StageStatus } from "./researchEvents";
import { formatElapsedDuration } from "./format";

export interface PlanStepDefinition {
  key: string;
  label: string;
  stageKeys: StageName[];
}

export const PLAN_STEP_DEFINITIONS: PlanStepDefinition[] = [
  { key: "plan", label: "Decompose the question into search axes", stageKeys: ["plan"] },
  { key: "search", label: "Search the selected sources", stageKeys: ["search"] },
  { key: "extract", label: "Read the sources and extract evidence", stageKeys: ["extract"] },
  { key: "verify", label: "Cross-check and verify the claims", stageKeys: ["score", "verify"] },
  { key: "synthesize", label: "Draft the cited brief", stageKeys: ["synthesize"] },
];

export const PLAN_STEP_COUNT = PLAN_STEP_DEFINITIONS.length;

export interface PlanStep {
  key: string;
  label: string;
  state: StageState;
  meta: string;
}

const PENDING_META = "queued";
const ACTIVE_META = "working…";
const DONE_META = "done";
const ERROR_META = "failed";
const META_SEPARATOR = " · ";
const DONE_STATUS: StageStatus = "done";

function earliestTimestamp(values: (string | null)[]): string | null {
  const present = values.filter((value): value is string => value !== null);
  if (present.length === 0) {
    return null;
  }
  return present.reduce((earliest, value) => (value < earliest ? value : earliest));
}

function latestTimestamp(values: (string | null)[]): string | null {
  const present = values.filter((value): value is string => value !== null);
  if (present.length === 0) {
    return null;
  }
  return present.reduce((latest, value) => (value > latest ? value : latest));
}

// Combines the constituent backend stage states for one step: error wins if
// any part errored, done only once every part is done, active if anything has
// started, otherwise pending.
export function combineStageStates(states: StageState[]): StageState {
  const substeps = states.flatMap((state) => state.substeps);
  const startedAt = earliestTimestamp(states.map((state) => state.startedAt));
  const doneAt = latestTimestamp(states.map((state) => state.doneAt));

  if (states.some((state) => state.status === "error")) {
    return { status: "error", startedAt, doneAt: null, substeps };
  }
  if (states.every((state) => state.status === DONE_STATUS)) {
    return { status: DONE_STATUS, startedAt, doneAt, substeps };
  }
  if (states.some((state) => state.status === "active" || state.status === DONE_STATUS)) {
    return { status: "active", startedAt, doneAt: null, substeps };
  }
  return { status: "pending", startedAt: null, doneAt: null, substeps: [] };
}

// The step's second line: "done · 12 sources" style for finished steps, the
// latest live substep for the one in flight.
export function planStepMeta(state: StageState): string {
  const latestSubstep = state.substeps.at(-1)?.message;

  switch (state.status) {
    case "done": {
      if (state.startedAt === null || state.doneAt === null) {
        return DONE_META;
      }
      return DONE_META + META_SEPARATOR + formatElapsedDuration(state.startedAt, state.doneAt);
    }
    case "active":
      return latestSubstep ?? ACTIVE_META;
    case "error":
      return ERROR_META;
    default:
      return PENDING_META;
  }
}

export function buildPlanSteps(streamState: ResearchStreamState): PlanStep[] {
  return PLAN_STEP_DEFINITIONS.map((definition) => {
    const state = combineStageStates(
      definition.stageKeys.map((stage) => streamState.stages[stage]),
    );
    return { key: definition.key, label: definition.label, state, meta: planStepMeta(state) };
  });
}

export function countCompletedSteps(steps: PlanStep[]): number {
  return steps.filter((step) => step.state.status === DONE_STATUS).length;
}
