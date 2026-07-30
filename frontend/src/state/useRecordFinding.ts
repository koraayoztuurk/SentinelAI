// Finding mutation hook.
//
// Records a finding the analyst reached themselves and refreshes the
// investigation-scoped server state, so the Findings, Timeline and Graph
// regions pick it up (the graph is seeded from findings' related entities).

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ApiError, toApiError } from "../communication/errors";
import {
  createFinding,
  type FindingCreateInput,
} from "../communication/investigations";
import { invalidateInvestigationData } from "./query";

export interface RecordFindingState {
  readonly record: (input: FindingCreateInput) => void;
  readonly recording: boolean;
  readonly error: ApiError | null;
}

export function useRecordFinding(investigationId: string): RecordFindingState {
  const client = useQueryClient();
  const mutation = useMutation({
    mutationFn: (input: FindingCreateInput) =>
      createFinding(investigationId, input),
    onSuccess: () => void invalidateInvestigationData(client, investigationId),
  });

  return {
    record: (input) => mutation.mutate(input),
    recording: mutation.isPending,
    error: toApiError(mutation.error),
  };
}
