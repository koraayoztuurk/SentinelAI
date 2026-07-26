// Platform status query hook (ES-070).
//
// A thin adapter over TanStack Query mirroring the other server-state hooks:
// it consumes the centralized `platformStatusQuery` builder and projects the
// query into `{ status, loading, error, retry }`. `retry` routes through the
// invalidate helper.

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ApiError, toApiError } from "../communication/errors";
import type { PlatformStatusViewModel } from "../communication/platform";
import { invalidatePlatformStatus, platformStatusQuery } from "./query";

export interface PlatformStatusState {
  readonly status: PlatformStatusViewModel | null;
  readonly loading: boolean;
  readonly error: ApiError | null;
  readonly retry: () => void;
}

export function usePlatformStatus(): PlatformStatusState {
  const client = useQueryClient();
  const query = useQuery(platformStatusQuery());

  return {
    status: query.data ?? null,
    loading: query.isLoading,
    error: toApiError(query.error),
    retry: () => void invalidatePlatformStatus(client),
  };
}
