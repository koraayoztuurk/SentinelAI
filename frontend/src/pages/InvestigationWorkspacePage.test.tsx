import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { InvestigationWorkspacePage } from "./InvestigationWorkspacePage";
import { TestQueryProvider } from "../test/TestQueryProvider";
import { ApiError } from "../communication/errors";
import { loadInvestigationWorkspace } from "../communication/workspace";
import type { WorkspaceViewModel } from "../communication/workspace";

// The page is exercised against mocked communication loaders, keeping the
// loading/loaded/error rendering and the selection synchronization
// deterministic without any network.
vi.mock("../communication/workspace", () => ({
  loadInvestigationWorkspace: vi.fn(),
}));
vi.mock("../communication/trace", () => ({
  loadInvestigationTrace: vi.fn(() => Promise.resolve([])),
}));

const mockedLoad = vi.mocked(loadInvestigationWorkspace);

const viewModel: WorkspaceViewModel = {
  summary: {
    id: "inv-001",
    title: "Suspicious lateral movement on finance subnet",
    status: "active",
    priority: "high",
    owner: "analyst-erin",
    tenant: "default",
    createdAt: "2026-06-28T09:15:00Z",
  },
  findings: [
    {
      id: "fnd-001",
      status: "validated",
      confidence: 0.86,
      creator: "graph-analysis-agent",
      createdAt: "2026-06-28T10:05:00Z",
    },
  ],
  evidence: [
    {
      id: "ev-101",
      source: "edr",
      integrity: "verified",
      timestamp: "2026-06-28T09:20:00Z",
      content: "Unusual SMB session opened.",
      downloadable: false,
    },
    {
      id: "ev-110",
      source: "identity",
      integrity: "verified",
      timestamp: "2026-06-28T11:25:00Z",
      content: "Unrecognized workstation login.",
      downloadable: false,
    },
  ],
  timeline: [
    {
      id: "evidence:ev-101",
      kind: "evidence",
      reference: "ev-101",
      label: "edr",
      occurredAt: "2026-06-28T09:20:00Z",
    },
    {
      id: "finding:fnd-001",
      kind: "finding",
      reference: "fnd-001",
      label: "graph-analysis-agent",
      occurredAt: "2026-06-28T10:05:00Z",
    },
  ],
  findingEvidence: { "fnd-001": ["ev-101"] },
  seedEntities: [],
};

function renderAt(path: string) {
  return render(
    <TestQueryProvider>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route
            path="/investigations/:id/workspace"
            element={<InvestigationWorkspacePage />}
          />
        </Routes>
      </MemoryRouter>
    </TestQueryProvider>,
  );
}

describe("InvestigationWorkspacePage", () => {
  beforeEach(() => {
    mockedLoad.mockReset();
  });

  it("renders the workspace regions", async () => {
    mockedLoad.mockResolvedValue(viewModel);
    renderAt("/investigations/inv-001/workspace");

    expect(
      await screen.findByText("Suspicious lateral movement on finance subnet"),
    ).toBeInTheDocument();
    expect(screen.getByText("Graph")).toBeInTheDocument();
    // AI Insights is a live region since ES-047 (run + trace).
    expect(screen.getByText("AI Insights")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Run investigation" }),
    ).toBeInTheDocument();
    // The Memory region remains a placeholder (no backend source yet).
    expect(screen.getByText("Memory")).toBeInTheDocument();
  });

  it("highlights supporting evidence when a finding is selected", async () => {
    mockedLoad.mockResolvedValue(viewModel);
    renderAt("/investigations/inv-001/workspace");

    // The finding id also appears in the Timeline, so target the finding card
    // button specifically (its accessible name includes the id).
    const findingCard = await screen.findByRole("button", { name: /fnd-001/ });
    // No highlight until the analyst selects the finding.
    expect(screen.queryByText("supports finding")).not.toBeInTheDocument();

    await userEvent.click(findingCard);

    // ev-101 backs fnd-001, so it becomes highlighted via the shared context.
    expect(await screen.findByText("supports finding")).toBeInTheDocument();
  });

  it("shows an error state when loading fails", async () => {
    mockedLoad.mockRejectedValue(
      new ApiError("investigation.not_found", "Investigation not found.", 404),
    );
    renderAt("/investigations/missing/workspace");

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "investigation.not_found",
    );
  });
});
