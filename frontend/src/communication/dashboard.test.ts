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
    });
  });

  it("keeps only confirmed findings (validated/accepted)", () => {
    const vm = toDashboardViewModel(sampleInvestigation, sampleFindings);
    expect(vm.findings.map((f) => f.id)).toEqual(["fnd-001", "fnd-002"]);
    expect(vm.findings.every((f) => f.status !== "proposed")).toBe(true);
  });
});
