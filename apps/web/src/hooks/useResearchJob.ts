import { useEffect, useState } from "react";

import {
  getClaims,
  getGraph,
  getJobSummary,
  getReport,
  getSources,
} from "../api/client";
import { JOB_POLL_INTERVAL_MS } from "../constants";
import type {
  Claim,
  EvidenceGraph,
  ResearchJobSummary,
  Source,
} from "../api/types";

const COMPLETED_STATUS = "completed";
const FAILED_STATUS = "failed";

export interface ResearchJobData {
  summary: ResearchJobSummary | null;
  claims: Claim[];
  sources: Source[];
  graph: EvidenceGraph | null;
  report: string;
  isComplete: boolean;
}

const EMPTY_JOB_DATA: ResearchJobData = {
  summary: null,
  claims: [],
  sources: [],
  graph: null,
  report: "",
  isComplete: false,
};

export function useResearchJob(researchId: string | null): ResearchJobData {
  const [data, setData] = useState<ResearchJobData>(EMPTY_JOB_DATA);

  useEffect(() => {
    if (researchId === null) {
      setData(EMPTY_JOB_DATA);
      return;
    }

    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;

    async function poll(): Promise<void> {
      const currentId = researchId as string;
      const summary = await getJobSummary(currentId);
      if (cancelled) {
        return;
      }

      const isTerminal =
        summary.status === COMPLETED_STATUS ||
        summary.status === FAILED_STATUS;

      if (summary.status === COMPLETED_STATUS) {
        const [claims, sources, graph, report] = await Promise.all([
          getClaims(currentId),
          getSources(currentId),
          getGraph(currentId),
          getReport(currentId),
        ]);
        if (cancelled) {
          return;
        }
        setData({
          summary,
          claims,
          sources,
          graph,
          report: report.report,
          isComplete: true,
        });
        return;
      }

      setData((previous) => ({ ...previous, summary }));
      if (!isTerminal) {
        timer = setTimeout(poll, JOB_POLL_INTERVAL_MS);
      }
    }

    void poll();
    return () => {
      cancelled = true;
      if (timer !== undefined) {
        clearTimeout(timer);
      }
    };
  }, [researchId]);

  return data;
}
