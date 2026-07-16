// Investigation outcome query hook (ES-055).
//
// A thin adapter over TanStack Query mirroring the other server-state hooks:
// it consumes the centralized `outcomeQuery` builder and projects the query
// into `{ outcome, loading, error, retry }`. `outcome` is null while none has
// been synthesized (0..1 semantics).

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ApiError, toApiError } from "../communication/errors";
import type { OutcomeViewModel } from "../communication/outcome";
import { invalidateOutcome, outcomeQuery } from "./query";

export interface OutcomeState {
  readonly outcome: OutcomeViewModel | null;
  readonly loading: boolean;
  readonly error: ApiError | null;
  readonly retry: () => void;
}

export function useInvestigationOutcome(id: string): OutcomeState {
  const client = useQueryClient();
  const query = useQuery(outcomeQuery(id));

  return {
    outcome: query.data ?? null,
    loading: query.isLoading,
    error: toApiError(query.error),
    retry: () => void invalidateOutcome(client, id),
  };
}
