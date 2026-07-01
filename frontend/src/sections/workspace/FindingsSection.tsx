// Findings region (investigation-workspace §5).
//
// Presents the confirmed (validated/accepted) findings — reused from the shared view
// model — while preserving traceability: selecting a finding drives the
// finding→evidence highlight in the Evidence Region through the shared Investigation
// Context.

import type { ConfirmedFindingViewModel } from "../../communication/dashboard";
import { useWorkspaceContext } from "../../state/workspaceContext";
import { WorkspaceFindingCard } from "../../components/workspace/WorkspaceFindingCard";
import { WorkspaceRegion } from "./WorkspaceRegion";

export interface FindingsSectionProps {
  readonly findings: readonly ConfirmedFindingViewModel[];
}

export function FindingsSection({ findings }: FindingsSectionProps) {
  const { state, dispatch } = useWorkspaceContext();

  return (
    <WorkspaceRegion title="Findings">
      {findings.length === 0 ? (
        <p className="text-sm opacity-50">No confirmed findings yet.</p>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2">
          {findings.map((finding) => (
            <WorkspaceFindingCard
              key={finding.id}
              finding={finding}
              selected={state.selectedFindingId === finding.id}
              onSelect={(findingId) =>
                dispatch({ type: "SELECT_FINDING", findingId })
              }
            />
          ))}
        </div>
      )}
    </WorkspaceRegion>
  );
}
