// Investigation erasure mutation hook (ES-066, ADR-017).
//
// A thin adapter over TanStack Query's mutation: erases the investigation and,
// on success, refreshes the investigation-scoped server state so every region
// re-renders the tombstone (redacted title, "erased" status, erased_at). The
// hook does not confirm — erasure is destructive and irreversible, so the UI
// gates it behind an explicit confirmation before calling `erase`.

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ApiError, toApiError } from "../communication/errors";
import { eraseInvestigation } from "../communication/investigations";
import { invalidateInvestigationData } from "./query";

export interface EraseInvestigationState {
  readonly erase: () => void;
  readonly erasing: boolean;
  readonly erased: boolean;
  readonly error: ApiError | null;
}

export function useEraseInvestigation(id: string): EraseInvestigationState {
  const client = useQueryClient();
  const mutation = useMutation({
    mutationFn: () => eraseInvestigation(id),
    onSuccess: () => void invalidateInvestigationData(client, id),
  });

  return {
    erase: () => mutation.mutate(),
    erasing: mutation.isPending,
    erased: mutation.isSuccess,
    error: toApiError(mutation.error),
  };
}
