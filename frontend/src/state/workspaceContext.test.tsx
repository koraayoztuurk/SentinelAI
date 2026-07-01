import { describe, expect, it } from "vitest";
import {
  initialWorkspaceState,
  workspaceReducer,
  type WorkspaceContextState,
} from "./workspaceReducer";

describe("workspaceReducer", () => {
  it("selects a finding without discarding the evidence selection", () => {
    const start: WorkspaceContextState = {
      selectedFindingId: null,
      selectedEvidenceId: "ev-101",
    };
    const next = workspaceReducer(start, {
      type: "SELECT_FINDING",
      findingId: "fnd-001",
    });
    expect(next).toEqual({
      selectedFindingId: "fnd-001",
      selectedEvidenceId: "ev-101",
    });
  });

  it("selects evidence", () => {
    const next = workspaceReducer(initialWorkspaceState, {
      type: "SELECT_EVIDENCE",
      evidenceId: "ev-110",
    });
    expect(next.selectedEvidenceId).toBe("ev-110");
    expect(next.selectedFindingId).toBeNull();
  });

  it("clears every selection", () => {
    const start: WorkspaceContextState = {
      selectedFindingId: "fnd-001",
      selectedEvidenceId: "ev-101",
    };
    expect(workspaceReducer(start, { type: "CLEAR_SELECTION" })).toEqual(
      initialWorkspaceState,
    );
  });
});
