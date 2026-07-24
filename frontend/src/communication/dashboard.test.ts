import { describe, expect, it } from "vitest";
import { toDashboardViewModel } from "./dashboard";
import { sampleFindings, sampleInvestigation } from "../mocks/data";

describe("toDashboardViewModel", () => {
  it("maps the investigation summary fields", () => {
    const vm = toDashboardViewModel(sampleInvestigation, []);
    expect(vm.summary).toEqual({
      id: "inv-001",
      title: sampleInvestigation.title,
      status: "active",
      priority: "high",
      owner: "analyst-erin",
      tenant: "default",
      createdAt: sampleInvestigation.created_at,
      erased: false,
      erasedAt: null,
    });
  });

  it("derives the erased tombstone state from the status (ES-066)", () => {
    const tombstone = toDashboardViewModel(
      {
        ...sampleInvestigation,
        title: "[erased]",
        status: "erased",
        erased_at: "2026-07-23T12:00:00Z",
      },
      [],
    );
    expect(tombstone.summary.erased).toBe(true);
    expect(tombstone.summary.erasedAt).toBe("2026-07-23T12:00:00Z");
    expect(tombstone.summary.status).toBe("erased");
  });

  it("keeps only confirmed findings (validated/accepted)", () => {
    const vm = toDashboardViewModel(sampleInvestigation, sampleFindings);
    expect(vm.findings.map((f) => f.id)).toEqual(["fnd-001", "fnd-002"]);
    expect(vm.findings.every((f) => f.status !== "proposed")).toBe(true);
  });
});
