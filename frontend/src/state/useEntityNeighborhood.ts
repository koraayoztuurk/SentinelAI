// Entity neighbourhood query hook.
//
// A thin adapter over TanStack Query: it consumes the centralized
// `entityNeighborhoodQuery` builder (which bakes in `enabled: entityId !== null`, so
// the hook stays idle when no entity is focused) and projects the query into
// `{ graph, loading, error, retry }`. `retry` routes through the invalidate helper.

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ApiError, toApiError } from "../communication/errors";
import type { GraphViewModel } from "../communication/graph";
import { entityNeighborhoodQuery, invalidateEntityNeighborhood } from "./query";

export interface NeighborhoodState {
  readonly graph: GraphViewModel | null;
  readonly loading: boolean;
  readonly error: ApiError | null;
  readonly retry: () => void;
}

export function useEntityNeighborhood(
  entityId: string | null,
): NeighborhoodState {
  const client = useQueryClient();
  const query = useQuery(entityNeighborhoodQuery(entityId));

  return {
    graph: query.data ?? null,
    loading: query.isLoading,
    error: toApiError(query.error),
    retry: () => {
      if (entityId !== null) {
        void invalidateEntityNeighborhood(client, entityId);
      }
    },
  };
}
