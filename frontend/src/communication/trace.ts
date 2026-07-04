// Investigation Trace data access + view model (ES-047).
//
// Read-only access to the backend Trace API (ES-045). The DTO mirrors the
// backend response shape as a hand-written transitional copy (api-design
// §14a); the UI consumes the mapped `TraceEntryViewModel` only.

import { apiClient } from "./apiClient";

export interface TraceEntryDto {
  readonly id: string;
  readonly investigation_id: string;
  readonly kind: string;
  readonly actor: string;
  readonly summary: string;
  readonly reference: string;
  readonly created_at: string;
}

export interface TraceEntryViewModel {
  readonly id: string;
  readonly kind: string;
  readonly actor: string;
  readonly summary: string;
  readonly reference: string;
  readonly createdAt: string;
}

export function toTraceViewModel(
  entries: readonly TraceEntryDto[],
): readonly TraceEntryViewModel[] {
  // Append order is preserved: the backend returns the explainability
  // journal in exactly the order it was written.
  return entries.map((entry) => ({
    id: entry.id,
    kind: entry.kind,
    actor: entry.actor,
    summary: entry.summary,
    reference: entry.reference,
    createdAt: entry.created_at,
  }));
}

export async function loadInvestigationTrace(
  id: string,
  signal?: AbortSignal,
): Promise<readonly TraceEntryViewModel[]> {
  const entries = await apiClient.get<readonly TraceEntryDto[]>(
    `/api/v1/investigations/${encodeURIComponent(id)}/trace`,
    { signal },
  );
  return toTraceViewModel(entries);
}
