import { describe, expect, it } from "vitest";
import { toTraceViewModel } from "./trace";

describe("toTraceViewModel", () => {
  it("preserves append order and normalizes field names", () => {
    const viewModels = toTraceViewModel([
      {
        id: "t-b",
        investigation_id: "inv-1",
        kind: "planner_decision",
        actor: "planner-agent",
        summary: "decided",
        reference: "act-1",
        created_at: "2026-07-04T10:00:00Z",
      },
      {
        id: "t-a",
        investigation_id: "inv-1",
        kind: "loop_outcome",
        actor: "investigation-loop",
        summary: "completed",
        reference: "act-1",
        created_at: "2026-07-04T10:00:01Z",
      },
    ]);

    expect(viewModels.map((entry) => entry.id)).toEqual(["t-b", "t-a"]);
    expect(viewModels[0]?.createdAt).toBe("2026-07-04T10:00:00Z");
    expect(viewModels[1]?.kind).toBe("loop_outcome");
  });
});
