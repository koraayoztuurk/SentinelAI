import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { InvestigationDashboardPage } from "./InvestigationDashboardPage";
import { TestQueryProvider } from "../test/TestQueryProvider";
import { ApiError } from "../communication/errors";
import { loadInvestigationDashboard } from "../communication/dashboard";
import type { DashboardViewModel } from "../communication/dashboard";

// The page is exercised against a mocked communication loader (MSW powers the dev
// browser demo). This keeps the page's loading/loaded/error rendering deterministic.
vi.mock("../communication/dashboard", () => ({
  loadInvestigationDashboard: vi.fn(),
}));

const mockedLoad = vi.mocked(loadInvestigationDashboard);

const viewModel: DashboardViewModel = {
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
};

function renderAt(path: string) {
  return render(
    <TestQueryProvider>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route
            path="/investigations/:id"
            element={<InvestigationDashboardPage />}
          />
        </Routes>
      </MemoryRouter>
    </TestQueryProvider>,
  );
}

describe("InvestigationDashboardPage", () => {
  beforeEach(() => {
    mockedLoad.mockReset();
  });

  it("renders the populated dashboard", async () => {
    mockedLoad.mockResolvedValue(viewModel);
    renderAt("/investigations/inv-001");

    expect(
      await screen.findByText("Suspicious lateral movement on finance subnet"),
    ).toBeInTheDocument();
    expect(screen.getAllByText("active").length).toBeGreaterThan(0);
    expect(screen.getByText("86%")).toBeInTheDocument();
    // The three deferred sections render as placeholders.
    expect(screen.getByText("Active Objectives")).toBeInTheDocument();
    expect(screen.getByText("AI Insights")).toBeInTheDocument();
    expect(screen.getByText("Recent Activity")).toBeInTheDocument();
  });

  it("shows an error state when loading fails", async () => {
    mockedLoad.mockRejectedValue(
      new ApiError("investigation.not_found", "Investigation not found.", 404),
    );
    renderAt("/investigations/missing");

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "investigation.not_found",
    );
  });
});
