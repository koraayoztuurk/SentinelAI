// Evidence region (investigation-workspace §5).
//
// Lists the investigation's evidence and participates in cross-region
// synchronization: selecting evidence updates the shared Investigation Context, and
// the evidence that supports the currently selected finding is highlighted. The
// highlighted set is derived from the context + the finding→evidence index; it is
// never stored (Derived State, ui-state-management §5).
//
// ES-047 adds the first write interaction: a minimal attach form so the live
// create→evidence→run flow is completable from the browser. Submission goes
// through the server-state mutation hook; the region keeps no data of its own.
//
// ES-061 adds raw evidence payloads: a file upload stores the bytes in the
// content-addressed payload store and attaches evidence referencing the
// returned address, and downloadable evidence exposes a verified download.

import { useMemo, useRef, useState } from "react";
import type {
  EvidenceViewModel,
  FindingEvidenceIndex,
} from "../../communication/workspace";
import { useWorkspaceContext } from "../../state/workspaceContext";
import { selectHighlightedEvidenceIds } from "../../state/workspaceSelectors";
import { useAttachEvidence } from "../../state/useAttachEvidence";
import { useUploadEvidencePayload } from "../../state/useUploadEvidencePayload";
import { useDownloadEvidencePayload } from "../../state/useDownloadEvidencePayload";
import { EvidenceCard } from "../../components/workspace/EvidenceCard";
import { Button } from "../../ui/Button";
import { WorkspaceRegion } from "./WorkspaceRegion";

export interface EvidenceSectionProps {
  readonly investigationId: string;
  readonly evidence: readonly EvidenceViewModel[];
  readonly findingEvidence: FindingEvidenceIndex;
}

function AttachEvidenceForm({
  investigationId,
}: {
  readonly investigationId: string;
}) {
  const [source, setSource] = useState("");
  const [content, setContent] = useState("");
  const { attach, attaching, error } = useAttachEvidence(investigationId);

  const submit = () => {
    if (source.trim().length === 0 || content.trim().length === 0) {
      return;
    }
    attach({ source: source.trim(), integrity: "unverified", content: content.trim() });
    setSource("");
    setContent("");
  };

  return (
    <div className="mt-4 grid gap-2 border-t border-white/10 pt-3">
      <div className="flex gap-2">
        <input
          aria-label="Evidence source"
          placeholder="Source (e.g. edr)"
          value={source}
          className="w-32 rounded border border-white/20 bg-transparent px-2 py-1 text-sm"
          onChange={(event) => setSource(event.target.value)}
        />
        <input
          aria-label="Evidence content"
          placeholder="What was observed?"
          value={content}
          className="flex-1 rounded border border-white/20 bg-transparent px-2 py-1 text-sm"
          onChange={(event) => setContent(event.target.value)}
        />
        <Button
          className="rounded border border-white/20 px-3 py-1 text-sm disabled:opacity-40"
          onClick={submit}
          disabled={attaching}
        >
          {attaching ? "Adding…" : "Add evidence"}
        </Button>
      </div>
      {error && (
        <p role="alert" className="text-xs text-red-400">
          Could not attach evidence ({error.code}).
        </p>
      )}
    </div>
  );
}

function UploadEvidenceForm({
  investigationId,
}: {
  readonly investigationId: string;
}) {
  const [source, setSource] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const { upload, uploading, error } = useUploadEvidencePayload(investigationId);

  const submit = () => {
    if (source.trim().length === 0 || file === null) {
      return;
    }
    upload({ source: source.trim(), file });
    setSource("");
    setFile(null);
    if (inputRef.current) {
      inputRef.current.value = "";
    }
  };

  return (
    <div className="mt-3 grid gap-2 border-t border-white/10 pt-3">
      <p className="text-xs opacity-60">
        Upload a raw evidence file (stored content-addressed, referenced by hash).
      </p>
      <div className="flex flex-wrap items-center gap-2">
        <input
          aria-label="Payload evidence source"
          placeholder="Source (e.g. upload)"
          value={source}
          className="w-32 rounded border border-white/20 bg-transparent px-2 py-1 text-sm"
          onChange={(event) => setSource(event.target.value)}
        />
        <input
          ref={inputRef}
          type="file"
          aria-label="Evidence payload file"
          className="flex-1 text-xs"
          onChange={(event) => setFile(event.target.files?.[0] ?? null)}
        />
        <Button
          className="rounded border border-white/20 px-3 py-1 text-sm disabled:opacity-40"
          onClick={submit}
          disabled={uploading || file === null}
        >
          {uploading ? "Uploading…" : "Upload file"}
        </Button>
      </div>
      {error && (
        <p role="alert" className="text-xs text-red-400">
          Could not upload payload ({error.code}).
        </p>
      )}
    </div>
  );
}

export function EvidenceSection({
  investigationId,
  evidence,
  findingEvidence,
}: EvidenceSectionProps) {
  const { state, dispatch } = useWorkspaceContext();
  const { download, downloadingId, error: downloadError } =
    useDownloadEvidencePayload(investigationId);

  const highlighted = useMemo(
    () => selectHighlightedEvidenceIds(state.selectedFindingId, findingEvidence),
    [state.selectedFindingId, findingEvidence],
  );

  return (
    <WorkspaceRegion title="Evidence">
      {evidence.length === 0 ? (
        <p className="text-sm opacity-50">No evidence collected yet.</p>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2">
          {evidence.map((item) => (
            <EvidenceCard
              key={item.id}
              evidence={item}
              selected={state.selectedEvidenceId === item.id}
              highlighted={highlighted.has(item.id)}
              onSelect={(evidenceId) =>
                dispatch({ type: "SELECT_EVIDENCE", evidenceId })
              }
              onDownload={download}
              downloading={downloadingId === item.id}
            />
          ))}
        </div>
      )}
      {downloadError && (
        <p role="alert" className="mt-2 text-xs text-red-400">
          Could not download payload ({downloadError.code}).
        </p>
      )}
      <AttachEvidenceForm investigationId={investigationId} />
      <UploadEvidenceForm investigationId={investigationId} />
    </WorkspaceRegion>
  );
}
