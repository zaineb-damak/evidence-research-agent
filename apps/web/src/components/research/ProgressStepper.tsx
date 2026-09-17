// The centerpiece live-progress UI: five user-facing rows built from the six
// backend pipeline stages (src/models/schemas.py::NodeName). `score` and
// `verify` are combined into a single "Verifying claims" row — from the
// user's perspective both stages operate on the already-extracted claims
// (confidence scoring, then contradiction/verification) with no separate
// visible output in between, unlike plan/search/extract/synthesize, which
// each produce a distinct, user-legible artifact. Below the stepper, StatChips
// reflect the reducer's live `counts`.

import { useState } from "react";

import { formatUsd } from "../../lib/format";
import type { ResearchStreamState, StageState } from "../../lib/researchEvents";
import type { StageName } from "../../api/types";
import { StageRow } from "./StageRow";
import { StatChip } from "./StatChip";

interface StageRowDefinition {
  key: string;
  label: string;
  stageKeys: StageName[];
}

const STAGE_ROW_DEFINITIONS: StageRowDefinition[] = [
  { key: "plan", label: "Understanding the question", stageKeys: ["plan"] },
  { key: "search", label: "Searching sources", stageKeys: ["search"] },
  { key: "extract", label: "Extracting evidence", stageKeys: ["extract"] },
  { key: "verify", label: "Verifying claims", stageKeys: ["score", "verify"] },
  { key: "synthesize", label: "Writing the report", stageKeys: ["synthesize"] },
];

const SOURCES_FOUND_DETAIL_KEYS = ["sources_found", "sources_count"] as const;
const CLAIMS_EXTRACTED_DETAIL_KEYS = ["claims_extracted", "claims_count"] as const;

const SOURCES_STAT_LABEL = "Sources found";
const CLAIMS_STAT_LABEL = "Claims extracted";
const COST_STAT_LABEL = "Cost so far";

function firstCountValue(
  counts: Record<string, unknown>,
  keys: readonly string[],
): number {
  for (const key of keys) {
    const value = counts[key];
    if (typeof value === "number") {
      return value;
    }
  }
  return 0;
}

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

// Combines the constituent backend stage states for one display row: error
// wins if any part errored, done only once every part is done, active if
// anything has started, otherwise pending.
function combineStageStates(states: StageState[]): StageState {
  const substeps = states.flatMap((state) => state.substeps);
  const startedAt = earliestTimestamp(states.map((state) => state.startedAt));
  const doneAt = latestTimestamp(states.map((state) => state.doneAt));

  if (states.some((state) => state.status === "error")) {
    return { status: "error", startedAt, doneAt: null, substeps };
  }
  if (states.every((state) => state.status === "done")) {
    return { status: "done", startedAt, doneAt, substeps };
  }
  if (states.some((state) => state.status === "active" || state.status === "done")) {
    return { status: "active", startedAt, doneAt: null, substeps };
  }
  return { status: "pending", startedAt: null, doneAt: null, substeps: [] };
}

interface ProgressStepperProps {
  streamState: ResearchStreamState;
  onRetry: () => void;
}

export function ProgressStepper({ streamState, onRetry }: ProgressStepperProps) {
  const [expandedOverrides, setExpandedOverrides] = useState<Record<string, boolean>>({});

  const rows = STAGE_ROW_DEFINITIONS.map((definition) => ({
    ...definition,
    state: combineStageStates(definition.stageKeys.map((stage) => streamState.stages[stage])),
  }));

  function isRowExpanded(rowKey: string, defaultExpanded: boolean): boolean {
    return expandedOverrides[rowKey] ?? defaultExpanded;
  }

  function toggleRow(rowKey: string, defaultExpanded: boolean): void {
    setExpandedOverrides((previous) => ({
      ...previous,
      [rowKey]: !isRowExpanded(rowKey, defaultExpanded),
    }));
  }

  const sourcesFound = firstCountValue(streamState.counts, SOURCES_FOUND_DETAIL_KEYS);
  const claimsExtracted = firstCountValue(streamState.counts, CLAIMS_EXTRACTED_DETAIL_KEYS);

  return (
    <div className="progress-stepper">
      <ol className="progress-stepper__rows">
        {rows.map((row) => {
          const defaultExpanded = row.state.status === "active";
          return (
            <StageRow
              key={row.key}
              label={row.label}
              state={row.state}
              isExpanded={isRowExpanded(row.key, defaultExpanded)}
              onToggle={() => toggleRow(row.key, defaultExpanded)}
              onRetry={row.state.status === "error" ? onRetry : undefined}
              errorMessage={row.state.status === "error" ? streamState.error : undefined}
            />
          );
        })}
      </ol>

      <div className="progress-stepper__stats">
        <StatChip label={SOURCES_STAT_LABEL} value={String(sourcesFound)} />
        <StatChip label={CLAIMS_STAT_LABEL} value={String(claimsExtracted)} />
        <StatChip label={COST_STAT_LABEL} value={formatUsd(streamState.cost ?? 0)} />
      </div>
    </div>
  );
}
