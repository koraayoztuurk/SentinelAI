import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { GraphSection } from "./GraphSection";
import { WorkspaceProvider } from "../../state/workspaceContext";
import { loadEntityNeighborhood } from "../../communication/graph";
import type { GraphViewModel } from "../../communication/graph";

// Only the loader is mocked; the pure layout helpers stay real so EntityGraph
// renders the nodes.
vi.mock("../../communication/graph", async (importOriginal) => {
  const actual =
    await importOriginal<typeof import("../../communication/graph")>();
  return { ...actual, loadEntityNeighborhood: vi.fn() };
});

const mockedLoad = vi.mocked(loadEntityNeighborhood);

const graph: GraphViewModel = {
  seedId: "host-12",
  nodes: [
    { id: "host-12", displayName: "FIN-WS-12", type: "host", confidence: 0.9, isSeed: true },
    { id: "host-19", displayName: "FIN-WS-19", type: "host", confidence: 0.88, isSeed: false },
  ],
  edges: [
    { id: "rel-1", source: "host-12", target: "host-19", type: "connects_to", confidence: 0.84 },
  ],
};

function renderSection(seedEntities: readonly string[]) {
  return render(
    <WorkspaceProvider>
      <GraphSection seedEntities={seedEntities} />
    </WorkspaceProvider>,
  );
}

describe("GraphSection", () => {
  beforeEach(() => {
    mockedLoad.mockReset();
    mockedLoad.mockResolvedValue(graph);
  });

  it("shows the empty state when there are no seeds", () => {
    renderSection([]);
    expect(screen.getByText("No entities to explore yet.")).toBeInTheDocument();
  });

  it("loads and draws the neighbourhood when a seed is selected", async () => {
    renderSection(["host-12"]);
    // Idle until a seed is chosen.
    expect(mockedLoad).not.toHaveBeenCalled();

    await userEvent.click(screen.getByRole("button", { name: "host-12" }));

    expect(await screen.findByText("FIN-WS-12")).toBeInTheDocument();
    expect(screen.getByText("FIN-WS-19")).toBeInTheDocument();
    // The active seed chip is highlighted.
    expect(screen.getByRole("button", { name: "host-12" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(mockedLoad).toHaveBeenCalledWith("host-12", expect.anything());
  });

  it("re-centers on the clicked node while preserving the origin seed", async () => {
    renderSection(["host-12"]);
    await userEvent.click(screen.getByRole("button", { name: "host-12" }));
    await screen.findByText("FIN-WS-19");

    await userEvent.click(screen.getByText("FIN-WS-19"));

    await waitFor(() =>
      expect(mockedLoad).toHaveBeenCalledWith("host-19", expect.anything()),
    );
    // The origin seed chip stays highlighted after drilling down.
    expect(screen.getByRole("button", { name: "host-12" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
  });
});
