import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { MemorySection } from "./MemorySection";
import { TestQueryProvider } from "../../test/TestQueryProvider";
import { loadInvestigationMemory } from "../../communication/memory";
import type { MemoryItemViewModel } from "../../communication/memory";

vi.mock("../../communication/memory", async (importOriginal) => {
  const actual =
    await importOriginal<typeof import("../../communication/memory")>();
  return { ...actual, loadInvestigationMemory: vi.fn() };
});

const mockedMemory = vi.mocked(loadInvestigationMemory);

const items: readonly MemoryItemViewModel[] = [
  {
    id: "m-1",
    type: "attack_pattern",
    status: "verified",
    version: 2,
    confidence: 0.9,
    content: "C2 beacon every 60 seconds over TLS",
    createdAt: "2026-07-10T10:00:00Z",
  },
  {
    id: "m-2",
    type: "analyst_note",
    status: "candidate",
    version: 1,
    confidence: 0.6,
    content: "",
    createdAt: "2026-07-11T10:00:00Z",
  },
];

function renderSection() {
  return render(
    <TestQueryProvider>
      <MemorySection investigationId="inv-001" />
    </TestQueryProvider>,
  );
}

describe("MemorySection", () => {
  beforeEach(() => {
    mockedMemory.mockReset();
  });

  it("shows the empty state when the investigation has no memory", async () => {
    mockedMemory.mockResolvedValue([]);
    renderSection();
    expect(
      await screen.findByText(/No memory items yet/),
    ).toBeInTheDocument();
  });

  it("renders the memory items with type, status, version and confidence", async () => {
    mockedMemory.mockResolvedValue(items);
    renderSection();

    expect(
      await screen.findByText("C2 beacon every 60 seconds over TLS"),
    ).toBeInTheDocument();
    const listItems = screen.getAllByRole("listitem");
    expect(listItems).toHaveLength(2);
    expect(listItems[0]).toHaveTextContent("attack_pattern");
    expect(listItems[0]).toHaveTextContent("verified");
    expect(listItems[0]).toHaveTextContent("v2 · confidence 90%");
    expect(listItems[1]).toHaveTextContent("analyst_note");
    expect(listItems[1]).toHaveTextContent("candidate");
  });

  it("presents a load failure with a retry affordance", async () => {
    mockedMemory.mockRejectedValue(new Error("boom"));
    renderSection();

    expect(await screen.findByRole("alert")).toHaveTextContent(
      /Could not load memory/,
    );
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
  });
});
