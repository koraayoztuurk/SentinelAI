// Investigation trace query hook.
//
// A thin adapter over TanStack Query mirroring the other server-state hooks:
// it consumes the centralized `traceQuery` builder and projects the query into
// `{ entries, loading, error, retry }`. `retry` routes through the invalidate
// helper.

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ApiError, toApiError } from "../communication/errors";
import type { TraceEntryViewModel } from "../communication/trace";
import { invalidateTrace, traceQuery } from "./query";

export interface TraceState {
  readonly entries: readonly TraceEntryViewModel[];
  readonly loading: boolean;
  readonly error: ApiError | null;
  readonly retry: () => void;
}

export function useInvestigationTrace(id: string): TraceState {
  const client = useQueryClient();
  const query = useQuery(traceQuery(id));

  return {
    entries: query.data ?? [],
    loading: query.isLoading,
    error: toApiError(query.error),
    retry: () => void invalidateTrace(client, id),
  };
}
