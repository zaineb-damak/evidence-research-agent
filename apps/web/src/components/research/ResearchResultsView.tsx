// The finished-job view: a Report/Evidence tab pair (mirroring the old
// App.tsx's tab behavior) backed by useResearchResults, so revisiting a
// completed session from history is instant once cached.

import { useState } from "react";

import { useResearchResults } from "../../hooks/useResearchResults";
import { EvidenceExplorer } from "./EvidenceExplorer";
import { ReportView } from "./ReportView";

type ResultsTab = "report" | "evidence";

const REPORT_TAB_LABEL = "Report";
const EVIDENCE_TAB_LABEL = "Evidence";
const LOADING_MESSAGE = "Loading results…";
const ERROR_MESSAGE = "Couldn't load the results for this research job.";

interface ResearchResultsViewProps {
  researchId: string;
}

export function ResearchResultsView({ researchId }: ResearchResultsViewProps) {
  const [activeTab, setActiveTab] = useState<ResultsTab>("report");
  const results = useResearchResults(researchId, true);

  if (results.isLoading) {
    return <p className="research-results__status">{LOADING_MESSAGE}</p>;
  }
  const report = results.report.data;
  const claims = results.claims.data;
  const sources = results.sources.data;
  const graph = results.graph.data;
  if (
    results.isError ||
    report === undefined ||
    claims === undefined ||
    sources === undefined ||
    graph === undefined
  ) {
    return <p className="research-results__status">{ERROR_MESSAGE}</p>;
  }

  return (
    <div className="research-results">
      <nav className="research-results__tabs" role="tablist">
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === "report"}
          className={`research-results__tab${activeTab === "report" ? " research-results__tab--active" : ""}`}
          onClick={() => setActiveTab("report")}
        >
          {REPORT_TAB_LABEL}
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === "evidence"}
          className={`research-results__tab${activeTab === "evidence" ? " research-results__tab--active" : ""}`}
          onClick={() => setActiveTab("evidence")}
        >
          {EVIDENCE_TAB_LABEL}
        </button>
      </nav>

      {activeTab === "report" ? (
        <ReportView reportMarkdown={report.report} />
      ) : (
        <EvidenceExplorer claims={claims} sources={sources} graph={graph} />
      )}
    </div>
  );
}
