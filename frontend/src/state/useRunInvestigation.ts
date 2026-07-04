// Investigation run mutation hook (ES-047 — the first write flow).
//
// A thin adapter over TanStack Query's mutation: triggers the backend's
// synchronous Investigation Loop run (ES-044) and, on settlement, refreshes
// the investigation-scoped server state through the centralized invalidate
// helper — the run writes trace entries (and possibly more) on the backend.
// An `escalated`/`exhausted` run is a *successful* response carrying its
// outcome; only transport/authorization failures surface as errors.

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ApiError, toApiError } from "../communication/errors";
import { runInvestigation, type RunOutcomeViewModel } from "../communication/run";
import { invalidateInvestigationData } from "./query";

export interface RunState {
  readonly run: () => void;
  readonly running: boolean;
  readonly outcome: RunOutcomeViewModel | null;
  readonly error: ApiError | null;
}

export function useRunInvestigation(id: string): RunState {
  const client = useQueryClient();
  const mutation = useMutation({
    mutationFn: () => runInvestigation(id),
    onSettled: () => void invalidateInvestigationData(client, id),
  });

  return {
    run: () => mutation.mutate(),
    running: mutation.isPending,
    outcome: mutation.data ?? null,
    error: toApiError(mutation.error),
  };
}
