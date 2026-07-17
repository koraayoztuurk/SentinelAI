// Evidence payload upload mutation hook (ES-061).
//
// Uploads a picked file's raw bytes to the content-addressed payload store,
// then attaches an evidence item referencing the returned content address as
// its integrity value (the ES-060 two-step: store, then attach — two separate
// single-store operations, AC-14). The file name becomes the evidence's
// normalized content label; the raw bytes live in the payload store. On
// success the investigation-scoped server state is refreshed.

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ApiError, toApiError } from "../communication/errors";
import {
  attachEvidence,
  uploadEvidencePayload,
} from "../communication/investigations";
import { invalidateInvestigationData } from "./query";

export interface UploadEvidenceInput {
  readonly source: string;
  readonly file: File;
}

export interface UploadEvidencePayloadState {
  readonly upload: (input: UploadEvidenceInput) => void;
  readonly uploading: boolean;
  readonly error: ApiError | null;
}

export function useUploadEvidencePayload(
  investigationId: string,
): UploadEvidencePayloadState {
  const client = useQueryClient();
  const mutation = useMutation({
    mutationFn: async ({ source, file }: UploadEvidenceInput) => {
      const bytes = await file.arrayBuffer();
      const stored = await uploadEvidencePayload(investigationId, bytes);
      return attachEvidence(investigationId, {
        source,
        integrity: stored.address,
        content: file.name,
      });
    },
    onSuccess: () => void invalidateInvestigationData(client, investigationId),
  });

  return {
    upload: (input) => mutation.mutate(input),
    uploading: mutation.isPending,
    error: toApiError(mutation.error),
  };
}
