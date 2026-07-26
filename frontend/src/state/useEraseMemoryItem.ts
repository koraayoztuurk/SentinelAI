// Shared-knowledge erasure mutation hook (ES-070, RFC-005/ADR-019).
//
// Erases a Memory Item — the person-linked right-to-be-forgotten path on the
// shared knowledge layer — and refreshes the investigation's memory listing so
// the tombstone replaces the item in place.
//
// The hook does not confirm and does not check permission: erasure is
// destructive, so the UI gates it behind an explicit confirmation, and whether
// the identity may erase at all is the backend's decision (the capability
// gate). The UI only avoids *offering* a control that would always be refused.

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ApiError, toApiError } from "../communication/errors";
import { eraseMemoryItem } from "../communication/memory";
import { invalidateMemory } from "./query";

export interface EraseMemoryItemState {
  readonly erase: (memoryId: string) => void;
  readonly erasingId: string | null;
  readonly error: ApiError | null;
}

export function useEraseMemoryItem(investigationId: string): EraseMemoryItemState {
  const client = useQueryClient();
  const mutation = useMutation({
    mutationFn: (memoryId: string) => eraseMemoryItem(memoryId),
    onSuccess: () => void invalidateMemory(client, investigationId),
  });

  return {
    erase: (memoryId: string) => mutation.mutate(memoryId),
    erasingId: mutation.isPending ? (mutation.variables ?? null) : null,
    error: toApiError(mutation.error),
  };
}
