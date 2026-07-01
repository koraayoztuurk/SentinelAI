// Investigation workspace query hook.
//
// A thin adapter over TanStack Query mirroring `useInvestigationDashboard`: it
// consumes the centralized `workspaceQuery` option builder and projects the query
// into `{ viewModel, loading, error, retry }`. `retry` routes through the invalidate
// helper. Cancellation is handled by Query.

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ApiError, toApiError } from "../communication/errors";
import type { WorkspaceViewModel } from "../communication/workspace";
import { invalidateWorkspace, workspaceQuery } from "./query";

export interface WorkspaceState {
  readonly viewModel: WorkspaceViewModel | null;
  readonly loading: boolean;
  readonly error: ApiError | null;
  readonly retry: () => void;
}

export function useInvestigationWorkspace(id: string): WorkspaceState {
  const client = useQueryClient();
  const query = useQuery(workspaceQuery(id));

  return {
    viewModel: query.data ?? null,
    loading: query.isLoading,
    error: toApiError(query.error),
    retry: () => void invalidateWorkspace(client, id),
  };
}
