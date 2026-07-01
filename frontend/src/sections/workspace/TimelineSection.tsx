// Timeline region (investigation-workspace §5).
//
// Presents investigation events in chronological order so analysts can reconstruct
// attack progression. The events are Derived State (from evidence/finding
// timestamps); the region emphasizes the entry that refers to the currently selected
// artifact, staying synchronized with the shared Investigation Context.

import type { TimelineEventViewModel } from "../../communication/workspace";
import { useWorkspaceContext } from "../../state/workspaceContext";
import { TimelineEntry } from "../../components/workspace/TimelineEntry";
import { WorkspaceRegion } from "./WorkspaceRegion";

export interface TimelineSectionProps {
  readonly timeline: readonly TimelineEventViewModel[];
}

export function TimelineSection({ timeline }: TimelineSectionProps) {
  const { state } = useWorkspaceContext();

  function isEmphasized(event: TimelineEventViewModel): boolean {
    if (event.kind === "finding") {
      return event.reference === state.selectedFindingId;
    }
    return event.reference === state.selectedEvidenceId;
  }

  return (
    <WorkspaceRegion title="Timeline">
      {timeline.length === 0 ? (
        <p className="text-sm opacity-50">No investigation activity yet.</p>
      ) : (
        <ol className="flex flex-col gap-1">
          {timeline.map((event) => (
            <TimelineEntry
              key={event.id}
              event={event}
              emphasized={isEmphasized(event)}
            />
          ))}
        </ol>
      )}
    </WorkspaceRegion>
  );
}
