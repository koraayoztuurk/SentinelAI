import { describe, expect, it } from "vitest";
import {
  selectHighlightedEvidenceIds,
  selectIsTimelineEventEmphasized,
} from "./workspaceSelectors";
import { initialWorkspaceState } from "./workspaceReducer";
import type { TimelineEventViewModel } from "../communication/workspace";

describe("selectHighlightedEvidenceIds", () => {
  it("is empty when no finding is selected", () => {
    expect(selectHighlightedEvidenceIds(null, { "fnd-001": ["ev-101"] }).size).toBe(0);
  });

  it("returns the selected finding's supporting evidence", () => {
    const ids = selectHighlightedEvidenceIds("fnd-001", {
      "fnd-001": ["ev-101", "ev-102"],
    });
    expect([...ids]).toEqual(["ev-101", "ev-102"]);
  });
});

describe("selectIsTimelineEventEmphasized", () => {
  const findingEvent: TimelineEventViewModel = {
    id: "finding:fnd-001",
    kind: "finding",
    reference: "fnd-001",
    label: "agent",
    occurredAt: "2026-06-28T10:05:00Z",
  };

  it("emphasizes a finding event that matches the selected finding", () => {
    const state = { ...initialWorkspaceState, selectedFindingId: "fnd-001" };
    expect(selectIsTimelineEventEmphasized(state, findingEvent)).toBe(true);
  });

  it("does not emphasize an unrelated event", () => {
    expect(
      selectIsTimelineEventEmphasized(initialWorkspaceState, findingEvent),
    ).toBe(false);
  });
});
