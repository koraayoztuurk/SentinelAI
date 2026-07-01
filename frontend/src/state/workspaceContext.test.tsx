import { describe, expect, it } from "vitest";
import {
  initialWorkspaceState,
  workspaceReducer,
  type WorkspaceContextState,
} from "./workspaceReducer";

describe("workspaceReducer", () => {
  it("selects a finding without discarding the evidence selection", () => {
    const start: WorkspaceContextState = {
      ...initialWorkspaceState,
      selectedEvidenceId: "ev-101",
    };
    const next = workspaceReducer(start, {
      type: "SELECT_FINDING",
      findingId: "fnd-001",
    });
    expect(next).toEqual({
      ...initialWorkspaceState,
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

  it("selecting a seed entity sets both the seed and the focus", () => {
    const next = workspaceReducer(initialWorkspaceState, {
      type: "SELECT_SEED_ENTITY",
      entityId: "host-12",
    });
    expect(next.selectedSeedEntityId).toBe("host-12");
    expect(next.selectedEntityId).toBe("host-12");
  });

  it("selecting an entity moves only the focus, preserving the origin seed", () => {
    const start: WorkspaceContextState = {
      ...initialWorkspaceState,
      selectedSeedEntityId: "host-12",
      selectedEntityId: "host-12",
    };
    const next = workspaceReducer(start, {
      type: "SELECT_ENTITY",
      entityId: "host-19",
    });
    expect(next.selectedEntityId).toBe("host-19");
    expect(next.selectedSeedEntityId).toBe("host-12");
  });

  it("clears every selection", () => {
    const start: WorkspaceContextState = {
      selectedFindingId: "fnd-001",
      selectedEvidenceId: "ev-101",
      selectedSeedEntityId: "host-12",
      selectedEntityId: "host-19",
    };
    expect(workspaceReducer(start, { type: "CLEAR_SELECTION" })).toEqual(
      initialWorkspaceState,
    );
  });
});
