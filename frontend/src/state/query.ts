// Server-state boundary (TanStack Query, thin layer).
//
// Backend data is cached, not owned (Frontend Architecture §8). This module is the
// single place the Query library is configured and keyed: the `QueryClient`, the
// central `queryKeys`, the per-resource query option builders and small invalidate
// helpers. Hooks call `useQuery(workspaceQuery(id))` and never assemble query
// options or call `invalidateQueries` directly, so caching/retry/enabled policy and
// the key vocabulary stay in one place (the server-state counterpart of the single
// `apiClient` communication boundary).

import { QueryClient, queryOptions } from "@tanstack/react-query";
import { loadInvestigationDashboard } from "../communication/dashboard";
import { loadInvestigationWorkspace } from "../communication/workspace";
import { loadEntityNeighborhood } from "../communication/graph";
import { loadInvestigationTrace } from "../communication/trace";

export function createQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        refetchOnWindowFocus: false,
        staleTime: 30_000,
      },
    },
  });
}

// The single key vocabulary. Every server-state query is identified here so keys
// never drift between the query definitions and the invalidate helpers.
export const queryKeys = {
  dashboard: (id: string) => ["dashboard", id] as const,
  workspace: (id: string) => ["workspace", id] as const,
  entityNeighborhood: (entityId: string) =>
    ["graph", "neighborhood", entityId] as const,
  trace: (id: string) => ["trace", id] as const,
};

// Query option builders — the only place per-query options live. Hooks consume
// these so staleTime/enabled/queryFn stay centralized.

export function dashboardQuery(id: string) {
  return queryOptions({
    queryKey: queryKeys.dashboard(id),
    queryFn: ({ signal }) => loadInvestigationDashboard(id, signal),
  });
}

export function workspaceQuery(id: string) {
  return queryOptions({
    queryKey: queryKeys.workspace(id),
    queryFn: ({ signal }) => loadInvestigationWorkspace(id, signal),
  });
}

export function traceQuery(id: string) {
  return queryOptions({
    queryKey: queryKeys.trace(id),
    queryFn: ({ signal }) => loadInvestigationTrace(id, signal),
  });
}

export function entityNeighborhoodQuery(entityId: string | null) {
  return queryOptions({
    // The key is never read while disabled; use a stable placeholder for null.
    queryKey: queryKeys.entityNeighborhood(entityId ?? "__none__"),
    queryFn: ({ signal }) => loadEntityNeighborhood(entityId as string, signal),
    enabled: entityId !== null,
  });
}

// Invalidate helpers — the only sanctioned way to invalidate server-state. Retry
// buttons and future mutations route through these instead of touching the client.

export function invalidateDashboard(client: QueryClient, id: string): Promise<void> {
  return client.invalidateQueries({ queryKey: queryKeys.dashboard(id) });
}

export function invalidateWorkspace(client: QueryClient, id: string): Promise<void> {
  return client.invalidateQueries({ queryKey: queryKeys.workspace(id) });
}

export function invalidateEntityNeighborhood(
  client: QueryClient,
  entityId: string,
): Promise<void> {
  return client.invalidateQueries({
    queryKey: queryKeys.entityNeighborhood(entityId),
  });
}

export function invalidateTrace(client: QueryClient, id: string): Promise<void> {
  return client.invalidateQueries({ queryKey: queryKeys.trace(id) });
}

// A run and an evidence attachment change investigation-scoped server state
// across regions; refreshing the workspace family in one place keeps the
// invalidation vocabulary centralized.
export function invalidateInvestigationData(
  client: QueryClient,
  id: string,
): Promise<void> {
  return Promise.all([
    invalidateWorkspace(client, id),
    invalidateDashboard(client, id),
    invalidateTrace(client, id),
  ]).then(() => undefined);
}
