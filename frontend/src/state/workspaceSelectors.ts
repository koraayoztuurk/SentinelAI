// Investigation Context selectors (pure, Derived State reads).
//
// Read-only derivations over the Investigation Context. Highlights are Derived State
// (UI State Management §5): reproducible from the authoritative selections, never
// stored. Formalizing them as selectors keeps the cross-region synchronization logic
// in one place instead of inline in each region.

import type { FindingEvidenceIndex, TimelineEventViewModel } from "../communication/workspace";
import type { WorkspaceContextState } from "./workspaceReducer";

// The evidence ids that support the currently selected finding — the set the
// Evidence Region highlights.
export function selectHighlightedEvidenceIds(
  selectedFindingId: string | null,
  findingEvidence: FindingEvidenceIndex,
): ReadonlySet<string> {
  if (selectedFindingId === null) {
    return new Set();
  }
  return new Set(findingEvidence[selectedFindingId] ?? []);
}

// Whether a timeline event refers to the currently selected artifact, so the
// Timeline Region can emphasize it.
export function selectIsTimelineEventEmphasized(
  state: WorkspaceContextState,
  event: TimelineEventViewModel,
): boolean {
  if (event.kind === "finding") {
    return event.reference === state.selectedFindingId;
  }
  return event.reference === state.selectedEvidenceId;
}
