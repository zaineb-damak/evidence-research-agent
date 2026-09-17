// Owns the live-progress read loop: opens the SSE connection (api/stream.ts),
// feeds decoded chunks through the pure parser (lib/sse.ts) and reducer
// (lib/researchEvents.ts), and reconnects with capped exponential backoff if
// the connection drops before a terminal event. Not React Query — this is a
// push stream, not a request/response resource (see hooks/useResearchResults.ts
// for the finished-job reads, which are).

import { useEffect, useRef, useState } from "react";

import { getJobSummary } from "../api/client";
import { streamResearchEvents } from "../api/stream";
import {
  applyProgressEvent,
  createInitialStreamState,
  isTerminalStreamStatus,
  parseProgressEvent,
} from "../lib/researchEvents";
import type { ResearchStreamState } from "../lib/researchEvents";
import { SseParser } from "../lib/sse";

const RECONNECT_BASE_DELAY_MS = 1000;
const RECONNECT_MAX_ATTEMPTS = 5;
const SNAPSHOT_EVENT_TYPE = "snapshot";

export interface UseResearchStreamResult {
  state: ResearchStreamState;
  isConnected: boolean;
  isReconnecting: boolean;
}

// researchId === null means "don't connect" (e.g. the job is already
// terminal, so ResearchPage renders the finished view instead).
export function useResearchStream(researchId: string | null): UseResearchStreamResult {
  const [state, setState] = useState<ResearchStreamState>(createInitialStreamState());
  const [isConnected, setIsConnected] = useState(false);
  const [isReconnecting, setIsReconnecting] = useState(false);
  const stateRef = useRef(state);
  stateRef.current = state;

  useEffect(() => {
    const initial = createInitialStreamState();
    stateRef.current = initial;
    setState(initial);
    setIsConnected(false);
    setIsReconnecting(false);

    if (researchId === null) {
      return;
    }

    const id = researchId;
    const controller = new AbortController();
    let cancelled = false;
    let reconnectAttempt = 0;
    let reconnectTimer: ReturnType<typeof setTimeout> | undefined;

    function updateState(event: Parameters<typeof applyProgressEvent>[1]): void {
      const next = applyProgressEvent(stateRef.current, event);
      stateRef.current = next;
      setState(next);
    }

    async function resyncFromSnapshot(): Promise<void> {
      try {
        const summary = await getJobSummary(id);
        if (cancelled) {
          return;
        }
        updateState({
          research_id: id,
          event_type: SNAPSHOT_EVENT_TYPE,
          stage: null,
          status: summary.status,
          message: summary.error ?? "",
          detail: {},
          emitted_at: new Date().toISOString(),
        });
      } catch {
        // Resync is best-effort — fall through and try the live stream anyway.
      }
    }

    function scheduleReconnect(): void {
      if (cancelled || isTerminalStreamStatus(stateRef.current.overallStatus)) {
        return;
      }
      if (reconnectAttempt >= RECONNECT_MAX_ATTEMPTS) {
        return;
      }
      const delay = RECONNECT_BASE_DELAY_MS * 2 ** reconnectAttempt;
      reconnectAttempt += 1;
      setIsReconnecting(true);
      reconnectTimer = setTimeout(() => {
        void connect(true);
      }, delay);
    }

    async function connect(isReconnect: boolean): Promise<void> {
      if (isReconnect) {
        await resyncFromSnapshot();
        if (cancelled || isTerminalStreamStatus(stateRef.current.overallStatus)) {
          setIsReconnecting(false);
          return;
        }
      }

      const parser = new SseParser();
      try {
        for await (const chunk of streamResearchEvents(id, controller.signal)) {
          if (cancelled) {
            return;
          }
          setIsConnected(true);
          setIsReconnecting(false);
          reconnectAttempt = 0;
          for (const message of parser.push(chunk)) {
            const event = parseProgressEvent(message.data);
            if (event !== null) {
              updateState(event);
            }
          }
        }
      } catch {
        // Aborted (cleanup) or a network error — both fall through below.
      }

      if (cancelled) {
        return;
      }
      setIsConnected(false);
      if (!isTerminalStreamStatus(stateRef.current.overallStatus)) {
        scheduleReconnect();
      }
    }

    void connect(false);

    return () => {
      cancelled = true;
      controller.abort();
      if (reconnectTimer !== undefined) {
        clearTimeout(reconnectTimer);
      }
    };
  }, [researchId]);

  return { state, isConnected, isReconnecting };
}
