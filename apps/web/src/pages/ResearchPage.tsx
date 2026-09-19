// A single run: the agent's plan (live while it works, reconstructed from
// the persisted status once it is done), the key sources it read, the cited
// brief, and a follow-up bar pinned to the bottom of the scroll container.

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { createResearch, getJobSummary, getReport } from "../api/client";
import { FollowUpComposer } from "../components/research/FollowUpComposer";
import { ResearchPlanCard } from "../components/research/ResearchPlanCard";
import { ResearchResultsView } from "../components/research/ResearchResultsView";
import { MainHeader } from "../components/shell/MainHeader";
import type { HeaderBadgeTone } from "../components/shell/MainHeader";
import { DEFAULT_DEPTH, DEFAULT_SOURCE_TYPES, DEPTH_LABELS } from "../constants";
import { researchResultsQueryKey } from "../hooks/useResearchResults";
import { useResearchStream } from "../hooks/useResearchStream";
import { useSessions, SESSIONS_QUERY_KEY } from "../hooks/useSessions";
import { downloadMarkdown, reportFileName } from "../lib/download";
import { formatRunTimestamp } from "../lib/format";
import { isTerminalStreamStatus, streamStateFromStatus } from "../lib/researchEvents";
import { buildResearchPath, ROUTE_HOME } from "../routes";

const COMPLETED_STATUS = "completed";
const FAILED_STATUS = "failed";
const TERMINAL_JOB_STATUSES: ReadonlySet<string> = new Set([COMPLETED_STATUS, FAILED_STATUS]);

const LOADING_MESSAGE = "Loading…";
const NOT_FOUND_MESSAGE = "This research job couldn't be found.";
const FAILED_BANNER_MESSAGE = "This research run failed.";
const TRY_AGAIN_LABEL = "Try again";
const JOB_SUMMARY_QUERY_RESOURCE = "job-summary";

const BADGE_RUNNING = "Running";
const BADGE_COMPLETE = "Complete";
const BADGE_FAILED = "Failed";
const DEPTH_BADGE_SUFFIX = " depth";
const SOURCES_READ_SUFFIX = " sources read";
const NO_SOURCES_READ = 0;

export function ResearchPage() {
  const { researchId } = useParams<{ researchId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const id = researchId as string;

  const snapshotQuery = useQuery({
    queryKey: [JOB_SUMMARY_QUERY_RESOURCE, id],
    queryFn: () => getJobSummary(id),
  });
  const sessionsQuery = useSessions();

  const snapshotIsTerminal =
    snapshotQuery.data !== undefined && TERMINAL_JOB_STATUSES.has(snapshotQuery.data.status);

  // Only open the live stream once we know the snapshot and it isn't already
  // finished — a job that's already completed/failed never needs to connect.
  const shouldStream = snapshotQuery.data !== undefined && !snapshotIsTerminal;
  const stream = useResearchStream(shouldStream ? id : null);

  const isTerminal = snapshotIsTerminal || isTerminalStreamStatus(stream.state.overallStatus);
  const snapshotStatus = snapshotQuery.data?.status;
  const hasFailed =
    snapshotStatus === FAILED_STATUS || stream.state.overallStatus === FAILED_STATUS;

  // A run that was already finished when the page opened has no live stream,
  // so its steps come from the persisted status instead.
  const planState = useMemo(
    () =>
      snapshotIsTerminal && snapshotStatus !== undefined
        ? streamStateFromStatus(
            id,
            snapshotStatus,
            snapshotQuery.data?.error ?? null,
            new Date().toISOString(),
          )
        : stream.state,
    [id, snapshotIsTerminal, snapshotStatus, snapshotQuery.data?.error, stream.state],
  );

  // Same query key as the results view's report query, so the header's
  // Export button reuses the fetched report rather than asking again.
  const isComplete = snapshotStatus === COMPLETED_STATUS;
  const reportQuery = useQuery({
    queryKey: researchResultsQueryKey("report", id),
    queryFn: () => getReport(id),
    enabled: isComplete,
  });

  const session = sessionsQuery.data?.find((item) => item.research_id === id);
  const depth = session?.depth ?? DEFAULT_DEPTH;

  function handleExport(): void {
    if (reportQuery.data === undefined || snapshotQuery.data === undefined) {
      return;
    }
    downloadMarkdown(reportFileName(snapshotQuery.data.question), reportQuery.data.report);
  }

  function handleRetry(): void {
    navigate(ROUTE_HOME, { state: { prefillQuestion: snapshotQuery.data?.question ?? "" } });
  }

  // There is no follow-up endpoint on an existing run yet, so a follow-up
  // starts a new run carrying this run's depth.
  async function handleFollowUp(question: string): Promise<void> {
    const response = await createResearch({
      question,
      depth,
      sourceTypes: DEFAULT_SOURCE_TYPES,
    });
    await queryClient.invalidateQueries({ queryKey: SESSIONS_QUERY_KEY });
    navigate(buildResearchPath(response.research_id));
  }

  if (snapshotQuery.isLoading) {
    return (
      <div className="app-shell__content">
        <MainHeader title={LOADING_MESSAGE} badgeLabel="" />
        <p className="research-view__status">{LOADING_MESSAGE}</p>
      </div>
    );
  }

  if (snapshotQuery.isError || snapshotQuery.data === undefined) {
    return (
      <div className="app-shell__content">
        <MainHeader title={NOT_FOUND_MESSAGE} badgeLabel="" />
        <p className="research-view__status">{NOT_FOUND_MESSAGE}</p>
      </div>
    );
  }

  const summary = snapshotQuery.data;
  const isRunning = !isTerminal;
  let badgeLabel = BADGE_RUNNING;
  let badgeTone: HeaderBadgeTone = "running";
  if (hasFailed) {
    badgeLabel = BADGE_FAILED;
    badgeTone = "neutral";
  } else if (isTerminal) {
    badgeLabel = BADGE_COMPLETE;
    badgeTone = "neutral";
  }

  const sourcesRead = summary.counts.sources;

  return (
    <div className="app-shell__content">
      <MainHeader
        title={summary.question}
        badgeLabel={badgeLabel}
        badgeTone={badgeTone}
        onExport={reportQuery.data === undefined ? undefined : handleExport}
      />

      <div className="research-view">
        <div className="research-view__body">
          <div className="research-view__meta">
            {session !== undefined && (
              <span>{formatRunTimestamp(new Date(session.created_at))}</span>
            )}
            <span>{DEPTH_LABELS[depth] + DEPTH_BADGE_SUFFIX}</span>
            {sourcesRead > NO_SOURCES_READ && <span>{sourcesRead + SOURCES_READ_SUFFIX}</span>}
          </div>

          <h1 className="research-view__title">{summary.question}</h1>

          {hasFailed ? (
            <p className="research-view__error-banner" role="alert">
              {summary.error ?? FAILED_BANNER_MESSAGE}{" "}
              <button type="button" className="research-view__retry" onClick={handleRetry}>
                {TRY_AGAIN_LABEL}
              </button>
            </p>
          ) : (
            <ResearchPlanCard
              streamState={planState}
              isRunning={isRunning}
              onRetry={handleRetry}
            />
          )}

          {isTerminal && !hasFailed && <ResearchResultsView researchId={id} />}
        </div>

        <FollowUpComposer onSubmit={handleFollowUp} />
      </div>
    </div>
  );
}
