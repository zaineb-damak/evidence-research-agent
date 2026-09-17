// The composer: submits a new research question, invalidates the sidebar's
// session list so it picks up the new job immediately, and navigates to the
// live-progress page. If arriving from a stepper's "Try again" (see
// components/research/ProgressStepper.tsx / StageRow.tsx), the original
// question is prefilled via router state.

import { useQueryClient } from "@tanstack/react-query";
import { useLocation, useNavigate } from "react-router-dom";

import type { CreateResearchInput } from "../api/client";
import { createResearch } from "../api/client";
import { ResearchComposer } from "../components/research/ResearchComposer";
import { SESSIONS_QUERY_KEY } from "../hooks/useSessions";
import { buildResearchPath } from "../routes";

export interface HomeLocationState {
  prefillQuestion?: string;
}

export function HomePage() {
  const navigate = useNavigate();
  const location = useLocation();
  const queryClient = useQueryClient();

  const locationState = (location.state as HomeLocationState | null) ?? {};

  async function handleSubmit(input: CreateResearchInput): Promise<void> {
    const response = await createResearch(input);
    await queryClient.invalidateQueries({ queryKey: SESSIONS_QUERY_KEY });
    navigate(buildResearchPath(response.research_id));
  }

  return (
    <ResearchComposer onSubmit={handleSubmit} initialQuestion={locationState.prefillQuestion} />
  );
}
