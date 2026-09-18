// A finished run's output: the key sources it read, then the cited brief —
// with the evidence explorer one segment away, since every claim in the
// brief traces back to a source passage.

import { useState } from "react";

import { useResearchResults } from "../../hooks/useResearchResults";
import { EvidenceExplorer } from "./EvidenceExplorer";
import { KeySources } from "./KeySources";
import { ReportView } from "./ReportView";

type ResultsTab = "brief" | "evidence";

const TABS: { value: ResultsTab; label: string }[] = [
  { value: "brief", label: "Brief" },
  { value: "evidence", label: "Evidence" },
];

const DEFAULT_TAB: ResultsTab = "brief";
const LOADING_MESSAGE = "Loading results…";
const ERROR_MESSAGE = "Couldn't load the results for this research job.";
const TABS_LABEL = "Result view";

interface ResearchResultsViewProps {
  researchId: string;
}

export function ResearchResultsView({ researchId }: ResearchResultsViewProps) {
  const [activeTab, setActiveTab] = useState<ResultsTab>(DEFAULT_TAB);
  const results = useResearchResults(researchId, true);

  if (results.isLoading) {
    return <p className="research-view__status">{LOADING_MESSAGE}</p>;
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
    return <p className="research-view__status">{ERROR_MESSAGE}</p>;
  }

  return (
    <>
      <KeySources sources={sources} />

      <div className="segmented research-view__tabs" role="tablist" aria-label={TABS_LABEL}>
        {TABS.map((tab) => {
          const isActive = tab.value === activeTab;
          return (
            <button
              key={tab.value}
              type="button"
              role="tab"
              aria-selected={isActive}
              className={`segmented__segment${isActive ? " segmented__segment--active" : ""}`}
              onClick={() => setActiveTab(tab.value)}
            >
              {tab.label}
            </button>
          );
        })}
      </div>

      {activeTab === "brief" ? (
        <ReportView reportMarkdown={report.report} />
      ) : (
        <EvidenceExplorer claims={claims} sources={sources} graph={graph} />
      )}
    </>
  );
}
