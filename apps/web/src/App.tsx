import { useState } from "react";

import { clearToken, isAuthenticated } from "./api/auth";
import { UnauthorizedError, createResearch } from "./api/client";
import { EvidenceExplorer } from "./components/EvidenceExplorer";
import { LoginForm } from "./components/LoginForm";
import { ProgressView } from "./components/ProgressView";
import { ReportView } from "./components/ReportView";
import { ResearchForm, type ResearchFormSubmit } from "./components/ResearchForm";
import { useResearchJob } from "./hooks/useResearchJob";

type ActiveTab = "report" | "explorer";

export function App() {
  const [authenticated, setAuthenticated] = useState(isAuthenticated());
  const [researchId, setResearchId] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [activeTab, setActiveTab] = useState<ActiveTab>("explorer");
  const job = useResearchJob(researchId);

  function signOut(): void {
    clearToken();
    setResearchId(null);
    setAuthenticated(false);
  }

  async function handleSubmit(input: ResearchFormSubmit): Promise<void> {
    setIsSubmitting(true);
    try {
      const response = await createResearch(input);
      setResearchId(response.research_id);
    } catch (submitError) {
      if (submitError instanceof UnauthorizedError) {
        signOut();
      } else {
        throw submitError;
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  if (!authenticated) {
    return (
      <div className="app">
        <header>
          <h1>Evidence Research Agent</h1>
        </header>
        <LoginForm onAuthenticated={() => setAuthenticated(true)} />
      </div>
    );
  }

  return (
    <div className="app">
      <header>
        <h1>Evidence Research Agent</h1>
        <button type="button" className="sign-out" onClick={signOut}>
          Sign out
        </button>
      </header>

      <ResearchForm onSubmit={handleSubmit} isSubmitting={isSubmitting} />

      {job.summary !== null && !job.isComplete && (
        <ProgressView summary={job.summary} />
      )}

      {job.isComplete && job.graph !== null && (
        <section className="results">
          <nav className="tabs">
            <button
              type="button"
              className={activeTab === "explorer" ? "active" : ""}
              onClick={() => setActiveTab("explorer")}
            >
              Evidence Explorer
            </button>
            <button
              type="button"
              className={activeTab === "report" ? "active" : ""}
              onClick={() => setActiveTab("report")}
            >
              Report
            </button>
          </nav>

          {activeTab === "explorer" ? (
            <EvidenceExplorer
              claims={job.claims}
              sources={job.sources}
              graph={job.graph}
            />
          ) : (
            <ReportView reportMarkdown={job.report} />
          )}
        </section>
      )}
    </div>
  );
}
