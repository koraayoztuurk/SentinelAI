// Investigation memory query hook (ES-052).
//
// A thin adapter over TanStack Query mirroring the other server-state hooks:
// it consumes the centralized `memoryQuery` builder and projects the query
// into `{ items, loading, error, retry }`. `retry` routes through the
// invalidate helper.

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ApiError, toApiError } from "../communication/errors";
import type { MemoryItemViewModel } from "../communication/memory";
import { invalidateMemory, memoryQuery } from "./query";

export interface MemoryState {
  readonly items: readonly MemoryItemViewModel[];
  readonly loading: boolean;
  readonly error: ApiError | null;
  readonly retry: () => void;
}

export function useInvestigationMemory(id: string): MemoryState {
  const client = useQueryClient();
  const query = useQuery(memoryQuery(id));

  return {
    items: query.data ?? [],
    loading: query.isLoading,
    error: toApiError(query.error),
    retry: () => void invalidateMemory(client, id),
  };
}
