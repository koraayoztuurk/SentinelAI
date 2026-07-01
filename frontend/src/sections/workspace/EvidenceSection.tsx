// Evidence region (investigation-workspace §5).
//
// Lists the investigation's evidence and participates in cross-region
// synchronization: selecting evidence updates the shared Investigation Context, and
// the evidence that supports the currently selected finding is highlighted. The
// highlighted set is derived from the context + the finding→evidence index; it is
// never stored (Derived State, ui-state-management §5).

import { useMemo } from "react";
import type {
  EvidenceViewModel,
  FindingEvidenceIndex,
} from "../../communication/workspace";
import { useWorkspaceContext } from "../../state/workspaceContext";
import { selectHighlightedEvidenceIds } from "../../state/workspaceSelectors";
import { EvidenceCard } from "../../components/workspace/EvidenceCard";
import { WorkspaceRegion } from "./WorkspaceRegion";

export interface EvidenceSectionProps {
  readonly evidence: readonly EvidenceViewModel[];
  readonly findingEvidence: FindingEvidenceIndex;
}

export function EvidenceSection({
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
    </WorkspaceRegion>
  );
}
