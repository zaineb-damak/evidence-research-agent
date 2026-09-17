// Pure reducer turning a stream of backend ProgressEvents
// (src/models/progress.py::ProgressEvent, apps/api/events.py) into UI state
// for the ProgressStepper. No DOM/fetch dependency — hooks/useResearchStream.ts
// is the only caller, feeding it events parsed by lib/sse.ts.

import { STAGE_ORDER } from "../constants";
import type { ProgressEvent, ResearchStatus, StageName } from "../api/types";

export type StageStatus = "pending" | "active" | "done" | "error";

export interface StageSubstep {
  message: string;
  detail: Record<string, unknown>;
  at: string;
}

export interface StageState {
  status: StageStatus;
  startedAt: string | null;
  doneAt: string | null;
  substeps: StageSubstep[];
}

// "connecting" is the state before the first event (snapshot or otherwise)
// has arrived — distinct from any real ResearchStatus.
export type StreamOverallStatus = "connecting" | ResearchStatus;

export interface ResearchStreamState {
  stages: Record<StageName, StageState>;
  counts: Record<string, unknown>;
  cost: number | null;
  overallStatus: StreamOverallStatus;
  error: string | null;
}

const CONNECTING_STATUS: StreamOverallStatus = "connecting";
const TERMINAL_STREAM_STATUSES: ReadonlySet<StreamOverallStatus> = new Set([
  "completed",
  "failed",
]);

// Reverse of src/workflows/progress_emitter.py::STAGE_STARTED_STATUS — used to
// infer which stage is "current" from a persisted ResearchStatus on a
// reconnect SNAPSHOT event, which carries a status but no stage.
const STAGE_FOR_STATUS: Partial<Record<ResearchStatus, StageName>> = {
  planning: "plan",
  searching: "search",
  extracting: "extract",
  resolving: "score",
  verifying: "verify",
  synthesizing: "synthesize",
};

const COST_DETAIL_KEY = "cost_usd";

function createEmptyStageState(): StageState {
  return { status: "pending", startedAt: null, doneAt: null, substeps: [] };
}

export function createInitialStreamState(): ResearchStreamState {
  const stages = {} as Record<StageName, StageState>;
  for (const stage of STAGE_ORDER) {
    stages[stage] = createEmptyStageState();
  }
  return {
    stages,
    counts: {},
    cost: null,
    overallStatus: CONNECTING_STATUS,
    error: null,
  };
}

export function isTerminalStreamStatus(status: StreamOverallStatus): boolean {
  return TERMINAL_STREAM_STATUSES.has(status);
}

// JSON.parse's a `data:` payload into a ProgressEvent, or null if it isn't
// one (malformed/unexpected message) — callers should skip null results
// rather than throw, since a single bad frame shouldn't kill the stream.
export function parseProgressEvent(rawData: string): ProgressEvent | null {
  try {
    const parsed = JSON.parse(rawData) as Partial<ProgressEvent>;
    if (typeof parsed.event_type !== "string" || typeof parsed.status !== "string") {
      return null;
    }
    return parsed as ProgressEvent;
  } catch {
    return null;
  }
}

function withStage(
  state: ResearchStreamState,
  stage: StageName,
  update: Partial<StageState>,
): ResearchStreamState {
  return {
    ...state,
    stages: {
      ...state.stages,
      [stage]: { ...state.stages[stage], ...update },
    },
  };
}

function mergeCounts(
  state: ResearchStreamState,
  detail: Record<string, unknown>,
): ResearchStreamState {
  if (Object.keys(detail).length === 0) {
    return state;
  }
  const cost = COST_DETAIL_KEY in detail ? (detail[COST_DETAIL_KEY] as number) : state.cost;
  return { ...state, counts: { ...state.counts, ...detail }, cost };
}

// Marks every stage that isn't already `done` or `error` as `done`. Used on a
// terminal DONE event: the backend's synthesize node sets status COMPLETED in
// the same update that would otherwise produce its STAGE_COMPLETED event, so
// depending on timing the stream can reach DONE with a stage still sitting at
// `active` (or, defensively, `pending`) — the UI must never show a stage stuck
// short of done once the run has actually finished.
function completeAllStages(
  state: ResearchStreamState,
  fallbackDoneAt: string | null = null,
): ResearchStreamState {
  const stages = { ...state.stages };
  for (const stage of STAGE_ORDER) {
    const current = stages[stage];
    if (current.status !== "done" && current.status !== "error") {
      stages[stage] = {
        ...current,
        status: "done",
        doneAt: current.doneAt ?? fallbackDoneAt,
      };
    }
  }
  return { ...state, stages };
}

// Best-effort reconstruction of per-stage state from a coarse persisted
// ResearchStatus (used for the initial SNAPSHOT event and for the resync
// snapshot fetched before a reconnect) — every stage up to and including the
// current one is inferred done/active, later ones stay pending.
function applySnapshotStatus(
  state: ResearchStreamState,
  status: ResearchStatus,
): ResearchStreamState {
  if (status === "completed") {
    return completeAllStages(state);
  }
  if (status === "failed") {
    return state;
  }
  const currentStage = STAGE_FOR_STATUS[status];
  if (currentStage === undefined) {
    return state;
  }
  const currentIndex = STAGE_ORDER.indexOf(currentStage);
  const stages = { ...state.stages };
  STAGE_ORDER.forEach((stage, index) => {
    if (stages[stage].status === "error") {
      return;
    }
    if (index < currentIndex) {
      stages[stage] = { ...stages[stage], status: "done" };
    } else if (index === currentIndex) {
      stages[stage] = { ...stages[stage], status: "active" };
    }
  });
  return { ...state, stages };
}

export function applyProgressEvent(
  state: ResearchStreamState,
  event: ProgressEvent,
): ResearchStreamState {
  // Once a terminal status is reached, further events are ignored — an error
  // (or a stray late completion event) halts the stepper where it is.
  if (isTerminalStreamStatus(state.overallStatus)) {
    return state;
  }

  switch (event.event_type) {
    case "snapshot": {
      const withStatus = applySnapshotStatus(
        { ...state, overallStatus: event.status },
        event.status,
      );
      return mergeCounts(withStatus, event.detail);
    }

    case "stage_started": {
      if (event.stage === null) {
        return state;
      }
      const withStage_ = withStage(state, event.stage, {
        status: "active",
        startedAt: event.emitted_at,
      });
      return { ...withStage_, overallStatus: event.status };
    }

    case "substep": {
      if (event.stage === null) {
        return state;
      }
      const stage = state.stages[event.stage];
      const withSubstep = withStage(state, event.stage, {
        substeps: [
          ...stage.substeps,
          { message: event.message, detail: event.detail, at: event.emitted_at },
        ],
      });
      return mergeCounts(withSubstep, event.detail);
    }

    case "stage_completed": {
      if (event.stage === null) {
        return state;
      }
      const withStage_ = withStage(state, event.stage, {
        status: "done",
        doneAt: event.emitted_at,
      });
      return mergeCounts({ ...withStage_, overallStatus: event.status }, event.detail);
    }

    case "done": {
      const completed = completeAllStages(state, event.emitted_at);
      return mergeCounts({ ...completed, overallStatus: event.status }, event.detail);
    }

    case "error": {
      const activeStage = STAGE_ORDER.find(
        (stage) => state.stages[stage].status === "active",
      );
      const stages = { ...state.stages };
      if (activeStage !== undefined) {
        stages[activeStage] = { ...stages[activeStage], status: "error" };
      }
      return {
        ...state,
        stages,
        overallStatus: event.status,
        error: event.message,
      };
    }

    default:
      return state;
  }
}
