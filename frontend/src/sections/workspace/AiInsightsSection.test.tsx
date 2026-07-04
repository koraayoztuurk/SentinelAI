import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AiInsightsSection } from "./AiInsightsSection";
import { TestQueryProvider } from "../../test/TestQueryProvider";
import { loadInvestigationTrace } from "../../communication/trace";
import { runInvestigation } from "../../communication/run";
import type { TraceEntryViewModel } from "../../communication/trace";

vi.mock("../../communication/trace", async (importOriginal) => {
  const actual =
    await importOriginal<typeof import("../../communication/trace")>();
  return { ...actual, loadInvestigationTrace: vi.fn() };
});
vi.mock("../../communication/run", async (importOriginal) => {
  const actual =
    await importOriginal<typeof import("../../communication/run")>();
  return { ...actual, runInvestigation: vi.fn() };
});

const mockedTrace = vi.mocked(loadInvestigationTrace);
const mockedRun = vi.mocked(runInvestigation);

const entries: readonly TraceEntryViewModel[] = [
  {
    id: "t-1",
    kind: "planner_decision",
    actor: "planner-agent",
    summary: "decided GetInvestigationAction",
    reference: "act-1",
    createdAt: "2026-07-04T10:00:00Z",
  },
  {
    id: "t-2",
    kind: "loop_outcome",
    actor: "investigation-loop",
    summary: "completed after 1 cycle(s)",
    reference: "act-1",
    createdAt: "2026-07-04T10:00:01Z",
  },
];

function renderSection() {
  return render(
    <TestQueryProvider>
      <AiInsightsSection investigationId="inv-001" />
    </TestQueryProvider>,
  );
}

describe("AiInsightsSection", () => {
  beforeEach(() => {
    mockedTrace.mockReset();
    mockedRun.mockReset();
  });

  it("shows the empty state before any AI activity", async () => {
    mockedTrace.mockResolvedValue([]);
    renderSection();
    expect(
      await screen.findByText(/No AI activity yet/),
    ).toBeInTheDocument();
  });

  it("renders the trace entries in order", async () => {
    mockedTrace.mockResolvedValue(entries);
    renderSection();

    expect(
      await screen.findByText("decided GetInvestigationAction"),
    ).toBeInTheDocument();
    const items = screen.getAllByRole("listitem");
    expect(items[0]).toHaveTextContent("planner_decision");
    expect(items[1]).toHaveTextContent("loop_outcome");
  });

  it("runs the investigation and presents a completed outcome", async () => {
    mockedTrace.mockResolvedValue([]);
    mockedRun.mockResolvedValue({
      end: "completed",
      cycles: 2,
      failureCode: null,
      actions: [],
    });
    renderSection();

    await userEvent.click(
      await screen.findByRole("button", { name: "Run investigation" }),
    );

    const badge = await screen.findByTestId("run-outcome");
    expect(badge).toHaveTextContent("completed");
    expect(badge).toHaveTextContent("after 2 cycles");
    // The trace is refreshed after a run (invalidate → reload).
    expect(mockedTrace.mock.calls.length).toBeGreaterThan(1);
  });

  it("presents an escalated outcome with its stable failure code", async () => {
    mockedTrace.mockResolvedValue([]);
    mockedRun.mockResolvedValue({
      end: "escalated",
      cycles: 1,
      failureCode: "ai.llm_provider_error",
      actions: [],
    });
    renderSection();

    await userEvent.click(
      await screen.findByRole("button", { name: "Run investigation" }),
    );

    const badge = await screen.findByTestId("run-outcome");
    expect(badge).toHaveTextContent("escalated");
    expect(badge).toHaveTextContent("ai.llm_provider_error");
  });
});
