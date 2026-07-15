// Investigation-scoped Memory data access + view model (ES-052).
//
// Read-only access to the Memory listing API: the latest version of every
// Memory Item originating from an investigation. Memory is the shared
// knowledge layer — the backend scopes by `source_investigation_id` and this
// page presents, never owns. The DTO mirrors the backend response shape as a
// hand-written transitional copy (api-design §14a); the UI consumes the
// mapped `MemoryItemViewModel` only.

import { apiClient } from "./apiClient";

export interface MemoryItemDto {
  readonly id: string;
  readonly type: string;
  readonly source_investigation_id: string;
  readonly confidence: number;
  readonly status: string;
  readonly created_at: string;
  readonly version: number;
  readonly content: string;
}

export interface MemoryItemViewModel {
  readonly id: string;
  readonly type: string;
  readonly status: string;
  readonly version: number;
  readonly confidence: number;
  readonly content: string;
  readonly createdAt: string;
}

export function toMemoryViewModel(
  items: readonly MemoryItemDto[],
): readonly MemoryItemViewModel[] {
  return items.map((item) => ({
    id: item.id,
    type: item.type,
    status: item.status,
    version: item.version,
    confidence: item.confidence,
    content: item.content,
    createdAt: item.created_at,
  }));
}

export async function loadInvestigationMemory(
  id: string,
  signal?: AbortSignal,
): Promise<readonly MemoryItemViewModel[]> {
  const items = await apiClient.get<readonly MemoryItemDto[]>(
    `/api/v1/memory?investigation_id=${encodeURIComponent(id)}`,
    { signal },
  );
  return toMemoryViewModel(items);
}
