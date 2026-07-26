import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { MemorySection } from "./MemorySection";
import { TestQueryProvider } from "../../test/TestQueryProvider";
import {
  eraseMemoryItem,
  loadInvestigationMemory,
} from "../../communication/memory";
import type { MemoryItemViewModel } from "../../communication/memory";
import { loadPlatformStatus } from "../../communication/platform";
import type { PlatformStatusViewModel } from "../../communication/platform";

vi.mock("../../communication/memory", async (importOriginal) => {
  const actual =
    await importOriginal<typeof import("../../communication/memory")>();
  return {
    ...actual,
    loadInvestigationMemory: vi.fn(),
    eraseMemoryItem: vi.fn(),
  };
});

vi.mock("../../communication/platform", async (importOriginal) => {
  const actual =
    await importOriginal<typeof import("../../communication/platform")>();
  return { ...actual, loadPlatformStatus: vi.fn() };
});

const mockedMemory = vi.mocked(loadInvestigationMemory);
const mockedErase = vi.mocked(eraseMemoryItem);
const mockedStatus = vi.mocked(loadPlatformStatus);

// The section reads its capabilities from the platform surface; only that
// field matters here, so the rest is a neutral healthy posture.
function statusWith(capabilities: readonly string[]): PlatformStatusViewModel {
  return {
    environment: "test",
    version: "0.1.0",
    readiness: "ready",
    stores: [],
    providers: [],
    llmFallbacks: 0,
    deadLetters: 0,
    deferredErasures: 0,
    retentionDays: 0,
    retentionEnforced: false,
    investigationsErased: 0,
    retentionFailures: 0,
    payloadErasureStrategy: "delete",
    auditRetentionDays: 365,
    auditSink: "durable",
    auditDurable: true,
    auditWriteFailures: 0,
    capabilities,
  };
}

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
    mockedErase.mockReset();
    mockedStatus.mockReset();
    mockedStatus.mockResolvedValue(statusWith([]));
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

  // --- shared-knowledge erasure (ES-070, ADR-019) ---

  it("offers no erase control without the capability", async () => {
    // Offering a control that would only ever be refused is worse than not
    // offering it: it invites an analyst to attempt an action they cannot do.
    mockedMemory.mockResolvedValue(items);
    mockedStatus.mockResolvedValue(statusWith([]));
    renderSection();

    await screen.findByText("C2 beacon every 60 seconds over TLS");
    expect(screen.queryByRole("button", { name: "Erase" })).toBeNull();
  });

  it("offers the erase control to an identity granted the capability", async () => {
    mockedMemory.mockResolvedValue(items);
    mockedStatus.mockResolvedValue(statusWith(["knowledge:erase"]));
    renderSection();

    expect(
      await screen.findAllByRole("button", { name: "Erase" }),
    ).toHaveLength(2);
  });

  it("requires an explicit confirmation before erasing", async () => {
    // Destroying organizational knowledge is irreversible; one click must not
    // be enough.
    mockedMemory.mockResolvedValue(items);
    mockedStatus.mockResolvedValue(statusWith(["knowledge:erase"]));
    mockedErase.mockResolvedValue({ ...items[0]!, status: "erased" } as never);
    renderSection();

    const buttons = await screen.findAllByRole("button", { name: "Erase" });
    await userEvent.click(buttons[0]!);

    expect(screen.getByText("Erase permanently?")).toBeInTheDocument();
    expect(mockedErase).not.toHaveBeenCalled();

    await userEvent.click(screen.getByRole("button", { name: "Confirm" }));
    expect(mockedErase).toHaveBeenCalledWith("m-1");
  });

  it("does not offer to erase an already erased item", async () => {
    mockedMemory.mockResolvedValue([{ ...items[0]!, status: "erased" }]);
    mockedStatus.mockResolvedValue(statusWith(["knowledge:erase"]));
    renderSection();

    await screen.findByText("erased");
    expect(screen.queryByRole("button", { name: "Erase" })).toBeNull();
  });
});
