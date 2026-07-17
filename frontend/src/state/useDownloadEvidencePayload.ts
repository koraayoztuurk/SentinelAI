// Evidence payload download hook (ES-061).
//
// Fetches an evidence item's verified raw payload through the authenticated
// communication boundary (a plain anchor cannot carry the bearer token) and
// hands it to the browser as a file download. Server state is untouched — this
// is a read. Download failures (a 409 integrity mismatch, a 404 dangling
// payload) surface as an `ApiError` for the region to present.

import { useCallback, useState } from "react";
import { ApiError, toApiError } from "../communication/errors";
import { downloadEvidencePayload } from "../communication/investigations";

export interface DownloadEvidencePayloadState {
  readonly download: (evidenceId: string) => void;
  readonly downloadingId: string | null;
  readonly error: ApiError | null;
}

function triggerBrowserDownload(blob: Blob, fileName: string): void {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = fileName;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

export function useDownloadEvidencePayload(
  investigationId: string,
): DownloadEvidencePayloadState {
  const [downloadingId, setDownloadingId] = useState<string | null>(null);
  const [error, setError] = useState<ApiError | null>(null);

  const download = useCallback(
    (evidenceId: string) => {
      setDownloadingId(evidenceId);
      setError(null);
      downloadEvidencePayload(investigationId, evidenceId)
        .then((blob) => {
          triggerBrowserDownload(blob, `evidence-${evidenceId}.bin`);
        })
        .catch((cause) => setError(toApiError(cause)))
        .finally(() => setDownloadingId(null));
    },
    [investigationId],
  );

  return { download, downloadingId, error };
}
