// Evidence attachment mutation hook (ES-047).
//
// A thin adapter over TanStack Query's mutation: attaches one evidence item
// to the investigation and refreshes the investigation-scoped server state so
// the Evidence/Timeline regions reflect it.

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ApiError, toApiError } from "../communication/errors";
import {
  attachEvidence,
  type EvidenceCreateInput,
} from "../communication/investigations";
import { invalidateInvestigationData } from "./query";

export interface AttachEvidenceState {
  readonly attach: (input: EvidenceCreateInput) => void;
  readonly attaching: boolean;
  readonly error: ApiError | null;
}

export function useAttachEvidence(investigationId: string): AttachEvidenceState {
  const client = useQueryClient();
  const mutation = useMutation({
    mutationFn: (input: EvidenceCreateInput) =>
      attachEvidence(investigationId, input),
    onSuccess: () => void invalidateInvestigationData(client, investigationId),
  });

  return {
    attach: (input) => mutation.mutate(input),
    attaching: mutation.isPending,
    error: toApiError(mutation.error),
  };
}
