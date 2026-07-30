// Memory promotion mutation hook.
//
// Writes one Memory Item into the shared knowledge layer and refreshes the
// investigation's server state so the Memory region shows it. The embedding
// that makes it findable by future investigations is produced asynchronously by
// the outbox projector — the item appears here immediately, and becomes
// semantically retrievable once that projection lands.

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ApiError, toApiError } from "../communication/errors";
import {
  createMemoryItem,
  type MemoryCreateInput,
} from "../communication/memory";
import { invalidateInvestigationData } from "./query";

export interface PromoteMemoryState {
  readonly promote: (input: MemoryCreateInput) => void;
  readonly promoting: boolean;
  readonly error: ApiError | null;
}

export function usePromoteMemory(investigationId: string): PromoteMemoryState {
  const client = useQueryClient();
  const mutation = useMutation({
    mutationFn: (input: MemoryCreateInput) => createMemoryItem(input),
    onSuccess: () => void invalidateInvestigationData(client, investigationId),
  });

  return {
    promote: (input) => mutation.mutate(input),
    promoting: mutation.isPending,
    error: toApiError(mutation.error),
  };
}
