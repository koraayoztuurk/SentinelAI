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

import { useMemo, useState } from "react";
import type {
  EvidenceViewModel,
  FindingEvidenceIndex,
} from "../../communication/workspace";
import { useWorkspaceContext } from "../../state/workspaceContext";
import { selectHighlightedEvidenceIds } from "../../state/workspaceSelectors";
import { useAttachEvidence } from "../../state/useAttachEvidence";
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

export function EvidenceSection({
  investigationId,
  evidence,
  findingEvidence,
}: EvidenceSectionProps) {
  const { state, dispatch } = useWorkspaceContext();

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
            />
          ))}
        </div>
      )}
      <AttachEvidenceForm investigationId={investigationId} />
    </WorkspaceRegion>
  );
}
