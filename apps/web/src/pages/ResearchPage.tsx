// Reads :researchId from the route. First fetches the plain job snapshot to
// decide live vs. finished: a terminal status (from either the snapshot or
// the live stream reaching DONE/ERROR) renders the finished report/evidence
// view; otherwise the live progress stepper is mounted over the SSE stream.
// The original question is the page's heading, serif per the type scale.

import { useQuery } from "@tanstack/react-query";
import { useNavigate, useParams } from "react-router-dom";

import { getJobSummary } from "../api/client";
import { ProgressStepper } from "../components/research/ProgressStepper";
import { ResearchResultsView } from "../components/research/ResearchResultsView";
import { useResearchStream } from "../hooks/useResearchStream";
import { isTerminalStreamStatus } from "../lib/researchEvents";
import { ROUTE_HOME } from "../routes";

const TERMINAL_JOB_STATUSES = new Set(["completed", "failed"]);
const LOADING_MESSAGE = "Loading…";
const NOT_FOUND_MESSAGE = "This research job couldn't be found.";
const FAILED_BANNER_MESSAGE = "This research run failed.";
const TRY_AGAIN_LABEL = "Try again";

export function ResearchPage() {
  const { researchId } = useParams<{ researchId: string }>();
  const navigate = useNavigate();
  const id = researchId as string;

  const snapshotQuery = useQuery({
    queryKey: ["job-summary", id],
    queryFn: () => getJobSummary(id),
  });

  const snapshotIsTerminal =
    snapshotQuery.data !== undefined && TERMINAL_JOB_STATUSES.has(snapshotQuery.data.status);

  // Only open the live stream once we know the snapshot and it isn't already
  // finished — a job that's already completed/failed never needs to connect.
  const shouldStream = snapshotQuery.data !== undefined && !snapshotIsTerminal;
  const stream = useResearchStream(shouldStream ? id : null);

  const isTerminal = snapshotIsTerminal || isTerminalStreamStatus(stream.state.overallStatus);

  function handleRetry(): void {
    navigate(ROUTE_HOME, { state: { prefillQuestion: snapshotQuery.data?.question ?? "" } });
  }

  if (snapshotQuery.isLoading) {
    return <p className="research-page__status">{LOADING_MESSAGE}</p>;
  }

  if (snapshotQuery.isError || snapshotQuery.data === undefined) {
    return <p className="research-page__status">{NOT_FOUND_MESSAGE}</p>;
  }

  return (
    <div className="research-page">
      <h1 className="research-page__title">{snapshotQuery.data.question}</h1>

      {isTerminal ? (
        <>
          {snapshotQuery.data.status === "failed" && (
            <p className="research-page__error-banner" role="alert">
              {snapshotQuery.data.error ?? FAILED_BANNER_MESSAGE}{" "}
              <button type="button" className="research-page__retry" onClick={handleRetry}>
                {TRY_AGAIN_LABEL}
              </button>
            </p>
          )}
          <ResearchResultsView researchId={id} />
        </>
      ) : (
        <ProgressStepper streamState={stream.state} onRetry={handleRetry} />
      )}
    </div>
  );
}
