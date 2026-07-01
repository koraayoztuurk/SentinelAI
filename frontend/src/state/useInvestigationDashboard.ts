// Investigation dashboard query hook.
//
// A thin adapter over TanStack Query: it consumes the centralized `dashboardQuery`
// option builder (so caching/retry policy stays in `state/query`) and projects the
// query into the UI-facing `{ viewModel, loading, error, retry }` shape. `retry`
// routes through the invalidate helper rather than touching the query client
// directly. Cancellation is handled by Query (the `signal` reaches the loader).

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ApiError, toApiError } from "../communication/errors";
import type { DashboardViewModel } from "../communication/dashboard";
import { dashboardQuery, invalidateDashboard } from "./query";

export interface DashboardState {
  readonly viewModel: DashboardViewModel | null;
  readonly loading: boolean;
  readonly error: ApiError | null;
  readonly retry: () => void;
}

export function useInvestigationDashboard(id: string): DashboardState {
  const client = useQueryClient();
  const query = useQuery(dashboardQuery(id));

  return {
    viewModel: query.data ?? null,
    loading: query.isLoading,
    error: toApiError(query.error),
    retry: () => void invalidateDashboard(client, id),
  };
}
