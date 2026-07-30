// Evidence region (investigation-workspace §5).
//
// Lists the investigation's evidence and participates in cross-region
// synchronization: selecting evidence updates the shared Investigation Context, and
// the evidence that supports the currently selected finding is highlighted. The
// highlighted set is derived from the context + the finding→evidence index; it is
// never stored (Derived State, ui-state-management §5).
//
// ES-047 adds the first write interaction: a minimal attach form so the live
// create→evidence→run flow is completable from the browser. ES-061 adds raw
// payloads: a file upload stores the bytes in the content-addressed payload
// store and attaches evidence referencing the returned address.
//
// Both write forms live behind a disclosure. Reading the evidence is the common
// case; adding to it is the occasional one, and a permanently open pair of
// forms makes the region look like data entry rather than a case file.

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
import { Disclosure } from "../../ui/Disclosure";
import { Empty } from "../../ui/Region";
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
    attach({
      source: source.trim(),
      integrity: "unverified",
      content: content.trim(),
    });
    setSource("");
    setContent("");
  };

  return (
    <div className="grid gap-2">
      <p className="text-xs text-ink-2">
        Write down something you observed. Where it came from matters as much as
        what it says.
      </p>
      <div className="flex flex-wrap gap-2">
        <input
          aria-label="Evidence source"
          placeholder="Source (e.g. edr)"
          value={source}
          className="input w-36"
          onChange={(event) => setSource(event.target.value)}
        />
        <input
          aria-label="Evidence content"
          placeholder="What was observed?"
          value={content}
          className="input min-w-40 flex-1"
          onChange={(event) => setContent(event.target.value)}
        />
        <Button variant="soft" onClick={submit} busy={attaching}>
          {attaching ? "Adding…" : "Add evidence"}
        </Button>
      </div>
      {error && (
        <p
          role="alert"
          className="rounded-input border border-coral/50 bg-coral/10 px-3 py-2 text-xs text-coral-ink"
        >
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
    <div className="grid gap-2">
      <p className="text-xs text-ink-2">
        The file is stored under a hash of its own contents, and the hash is
        checked again on download — so you can prove the bytes never changed.
      </p>
      <div className="flex flex-wrap items-center gap-2">
        <input
          aria-label="Payload evidence source"
          placeholder="Source (e.g. upload)"
          value={source}
          className="input w-36"
          onChange={(event) => setSource(event.target.value)}
        />
        <input
          ref={inputRef}
          type="file"
          aria-label="Evidence payload file"
          className="file-input mono-label min-w-40 flex-1 text-ink-2"
          onChange={(event) => setFile(event.target.files?.[0] ?? null)}
        />
        <Button
          variant="soft"
          onClick={submit}
          busy={uploading}
          disabled={file === null}
        >
          {uploading ? "Uploading…" : "Upload file"}
        </Button>
      </div>
      {error && (
        <p
          role="alert"
          className="rounded-input border border-coral/50 bg-coral/10 px-3 py-2 text-xs text-coral-ink"
        >
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
    <WorkspaceRegion
      title="Evidence"
      note="The raw observations this case rests on. Evidence is never edited — a correction is new evidence, so the original record always survives."
    >
      {evidence.length === 0 ? (
        <Empty>Nothing collected yet. Add the first observation below.</Empty>
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
        <p
          role="alert"
          className="mt-3 rounded-input border border-coral/50 bg-coral/10 px-3 py-2 text-xs text-coral-ink"
        >
          Could not download payload ({downloadError.code}).
        </p>
      )}

      <div className="mt-5 grid gap-4 border-t border-line pt-4">
        <Disclosure summary="Add an observation" defaultOpen={evidence.length === 0}>
          <AttachEvidenceForm investigationId={investigationId} />
        </Disclosure>
        <Disclosure summary="Upload a file as evidence">
          <UploadEvidenceForm investigationId={investigationId} />
        </Disclosure>
      </div>
    </WorkspaceRegion>
  );
}
