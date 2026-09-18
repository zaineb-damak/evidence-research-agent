// The empty / new-run screen: submits a new research question, invalidates
// the sidebar's session list so it picks up the new job immediately, and
// navigates to the run. If arriving from a failed run's "Try again", the
// original question is prefilled via router state.

import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import type { CreateResearchInput } from "../api/client";
import { createResearch } from "../api/client";
import type { ResearchDepth } from "../api/types";
import { ResearchComposer } from "../components/research/ResearchComposer";
import { MainHeader } from "../components/shell/MainHeader";
import { DEFAULT_DEPTH, DEPTH_LABELS } from "../constants";
import { SESSIONS_QUERY_KEY } from "../hooks/useSessions";
import { buildResearchPath } from "../routes";

export interface HomeLocationState {
  prefillQuestion?: string;
}

const HEADER_TITLE = "New research";
const DEPTH_BADGE_SUFFIX = " depth";

export function HomePage() {
  const navigate = useNavigate();
  const location = useLocation();
  const queryClient = useQueryClient();
  const [depth, setDepth] = useState<ResearchDepth>(DEFAULT_DEPTH);

  const locationState = (location.state as HomeLocationState | null) ?? {};

  async function handleSubmit(input: CreateResearchInput): Promise<void> {
    const response = await createResearch(input);
    await queryClient.invalidateQueries({ queryKey: SESSIONS_QUERY_KEY });
    navigate(buildResearchPath(response.research_id));
  }

  return (
    <div className="app-shell__content">
      <MainHeader
        title={HEADER_TITLE}
        badgeLabel={`${DEPTH_LABELS[depth]}${DEPTH_BADGE_SUFFIX}`}
      />
      <ResearchComposer
        depth={depth}
        onDepthChange={setDepth}
        onSubmit={handleSubmit}
        initialQuestion={locationState.prefillQuestion}
      />
    </div>
  );
}
