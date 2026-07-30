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

// Promotion into organizational memory.
//
// Domain Rule 5: only validated knowledge becomes persistent organizational
// memory, so a promotion always cites the confirmed findings it came from. The
// item is created `verified` — it is knowledge an analyst has already confirmed
// inside this investigation, not a candidate awaiting review.
export interface MemoryCreateInput {
  readonly type: string;
  readonly source_investigation_id: string;
  readonly confidence: number;
  readonly status: string;
  readonly content: string;
  readonly referenced_findings?: readonly string[];
}

export function createMemoryItem(
  input: MemoryCreateInput,
): Promise<MemoryItemDto> {
  return apiClient.post<MemoryItemDto>("/api/v1/memory", input);
}

// Person-linked erasure of shared knowledge (ES-070, ADR-019). Requires the
// `knowledge:erase` capability; the backend decides, this only calls.
export function eraseMemoryItem(
  memoryId: string,
): Promise<MemoryItemDto> {
  return apiClient.delete<MemoryItemDto>(
    `/api/v1/memory/${encodeURIComponent(memoryId)}`,
  );
}
