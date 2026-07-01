import { describe, expect, it } from "vitest";
import {
  buildFindingEvidenceIndex,
  collectSeedEntities,
  deriveTimelineEvents,
  toWorkspaceViewModel,
} from "./workspace";
import {
  sampleEvidence,
  sampleFindings,
  sampleInvestigation,
} from "../mocks/data";

describe("toWorkspaceViewModel", () => {
  it("reuses the shared summary and confirmed findings", () => {
    const vm = toWorkspaceViewModel(
      sampleInvestigation,
      sampleEvidence,
      sampleFindings,
    );
    // Summary is inherited from the dashboard view model, not redefined.
    expect(vm.summary.id).toBe("inv-001");
    expect(vm.summary.status).toBe("active");
    // The Findings region presents validated/accepted findings only.
    expect(vm.findings.map((f) => f.id)).toEqual(["fnd-001", "fnd-002"]);
  });

  it("projects evidence and composes the derived views", () => {
    const vm = toWorkspaceViewModel(
      sampleInvestigation,
      sampleEvidence,
      sampleFindings,
    );
    expect(vm.evidence.map((e) => e.id)).toEqual([
      "ev-101",
      "ev-102",
      "ev-110",
      "ev-120",
    ]);
    expect(vm.timeline).toHaveLength(
      sampleEvidence.length + sampleFindings.length,
    );
    expect(vm.findingEvidence["fnd-001"]).toEqual(["ev-101", "ev-102"]);
  });
});

describe("deriveTimelineEvents", () => {
  it("orders events chronologically across evidence and findings", () => {
    const events = deriveTimelineEvents(sampleEvidence, sampleFindings);
    const times = events.map((e) => Date.parse(e.occurredAt));
    const sorted = [...times].sort((a, b) => a - b);
    expect(times).toEqual(sorted);
  });

  it("tags each event with its origin kind and reference", () => {
    const events = deriveTimelineEvents(sampleEvidence, sampleFindings);
    const first = events[0];
    expect(first?.kind).toBe("evidence");
    expect(first?.reference).toBe("ev-101");
    expect(events.some((e) => e.kind === "finding")).toBe(true);
  });
});

describe("buildFindingEvidenceIndex", () => {
  it("maps every finding to its supporting evidence", () => {
    const index = buildFindingEvidenceIndex(sampleFindings);
    expect(index["fnd-001"]).toEqual(["ev-101", "ev-102"]);
    expect(index["fnd-002"]).toEqual(["ev-110"]);
    expect(index["fnd-003"]).toEqual(["ev-120"]);
  });
});

describe("collectSeedEntities", () => {
  it("collects the confirmed findings' related entities, deduplicated", () => {
    // fnd-003 is proposed (excluded); the seeds keep first-seen order.
    expect(collectSeedEntities(sampleFindings)).toEqual([
      "host-12",
      "host-19",
      "user-jdoe",
    ]);
  });
});
