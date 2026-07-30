// Investigation lifecycle mutation hook.
//
// Moves the investigation between its documented business states. The permitted
// transitions belong to the Investigation Service — an invalid one comes back as
// a stable error rather than being prevented here, so the client never encodes a
// business rule it does not own.

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ApiError, toApiError } from "../communication/errors";
import { changeInvestigationStatus } from "../communication/investigations";
import { invalidateInvestigationData } from "./query";

export interface ChangeStatusState {
  readonly change: (status: string) => void;
  readonly changing: boolean;
  readonly error: ApiError | null;
}

export function useChangeInvestigationStatus(
  investigationId: string,
): ChangeStatusState {
  const client = useQueryClient();
  const mutation = useMutation({
    mutationFn: (status: string) =>
      changeInvestigationStatus(investigationId, { status }),
    onSuccess: () => void invalidateInvestigationData(client, investigationId),
  });

  return {
    change: (status) => mutation.mutate(status),
    changing: mutation.isPending,
    error: toApiError(mutation.error),
  };
}
