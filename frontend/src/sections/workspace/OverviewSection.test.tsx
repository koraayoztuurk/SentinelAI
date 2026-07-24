import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { OverviewSection } from "./OverviewSection";
import { TestQueryProvider } from "../../test/TestQueryProvider";
import { eraseInvestigation } from "../../communication/investigations";
import type { InvestigationSummaryViewModel } from "../../communication/dashboard";

vi.mock("../../communication/investigations", async (importOriginal) => {
  const actual =
    await importOriginal<typeof import("../../communication/investigations")>();
  return { ...actual, eraseInvestigation: vi.fn() };
});

const mockedErase = vi.mocked(eraseInvestigation);

const liveSummary: InvestigationSummaryViewModel = {
  id: "inv-1",
  title: "Suspicious lateral movement",
  status: "active",
  priority: "high",
  owner: "analyst-erin",
  tenant: "acme",
  createdAt: "2026-06-28T09:15:00Z",
  erased: false,
  erasedAt: null,
};

function renderOverview(
  summary: InvestigationSummaryViewModel = liveSummary,
) {
  return render(
    <TestQueryProvider>
      <OverviewSection investigationId="inv-1" summary={summary} />
    </TestQueryProvider>,
  );
}

describe("OverviewSection data lifecycle (ES-066)", () => {
  beforeEach(() => {
    mockedErase.mockReset();
  });

  it("requires explicit confirmation before erasing", async () => {
    mockedErase.mockResolvedValue({
      id: "inv-1",
      title: "[erased]",
      status: "erased",
      created_at: "2026-06-28T09:15:00Z",
      owner: "analyst-erin",
      priority: "high",
      tenant: "acme",
      erased_at: "2026-07-23T12:00:00Z",
    });
    renderOverview();

    // The destructive action is not exposed as a single click.
    await userEvent.click(
      screen.getByRole("button", { name: "Erase investigation" }),
    );
    expect(mockedErase).not.toHaveBeenCalled();

    // Only after confirming does the erasure fire.
    await userEvent.click(
      screen.getByRole("button", { name: "Confirm erase" }),
    );
    await waitFor(() => expect(mockedErase).toHaveBeenCalledTimes(1));
    expect(mockedErase).toHaveBeenCalledWith("inv-1");
  });

  it("can back out of the confirmation without erasing", async () => {
    renderOverview();
    await userEvent.click(
      screen.getByRole("button", { name: "Erase investigation" }),
    );
    await userEvent.click(screen.getByRole("button", { name: "Cancel" }));

    expect(
      screen.queryByRole("button", { name: "Confirm erase" }),
    ).not.toBeInTheDocument();
    expect(mockedErase).not.toHaveBeenCalled();
  });

  it("renders the tombstone state for an erased investigation", () => {
    renderOverview({
      ...liveSummary,
      title: "[erased]",
      status: "erased",
      erased: true,
      erasedAt: "2026-07-23T12:00:00Z",
    });

    expect(
      screen.getByText(/was erased on 2026-07-23T12:00:00Z/),
    ).toBeInTheDocument();
    // No erase control on an already-erased investigation.
    expect(
      screen.queryByRole("button", { name: "Erase investigation" }),
    ).not.toBeInTheDocument();
  });
});
