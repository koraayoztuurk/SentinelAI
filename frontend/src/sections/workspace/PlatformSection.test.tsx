import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { PlatformSection } from "./PlatformSection";
import { TestQueryProvider } from "../../test/TestQueryProvider";
import { loadPlatformStatus } from "../../communication/platform";
import type { PlatformStatusViewModel } from "../../communication/platform";

vi.mock("../../communication/platform", async (importOriginal) => {
  const actual =
    await importOriginal<typeof import("../../communication/platform")>();
  return { ...actual, loadPlatformStatus: vi.fn() };
});

const mockedStatus = vi.mocked(loadPlatformStatus);

const healthy: PlatformStatusViewModel = {
  environment: "production",
  version: "0.1.0",
  readiness: "ready",
  stores: [
    { name: "postgres", state: "ok", gating: true },
    { name: "neo4j", state: "ok", gating: true },
    { name: "qdrant", state: "ok", gating: false },
  ],
  providers: [{ name: "nvidia", circuit: "closed" }],
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
  capabilities: [],
};

function renderSection() {
  return render(
    <TestQueryProvider>
      <PlatformSection />
    </TestQueryProvider>,
  );
}

describe("PlatformSection", () => {
  beforeEach(() => {
    mockedStatus.mockReset();
  });

  it("reports the platform as ready", async () => {
    mockedStatus.mockResolvedValue(healthy);

    renderSection();

    expect(await screen.findByText("ready")).toBeInTheDocument();
    expect(screen.getByText(/production/)).toBeInTheDocument();
  });

  it("distinguishes a degradable store from a gating one", async () => {
    // A derived store being unavailable is a reduced capability, not an
    // outage — the region must not present the two the same way.
    mockedStatus.mockResolvedValue({
      ...healthy,
      readiness: "degraded",
      stores: [
        { name: "postgres", state: "ok", gating: true },
        { name: "neo4j", state: "ok", gating: true },
        { name: "qdrant", state: "unavailable", gating: false },
      ],
    });

    renderSection();

    expect(await screen.findByText("degraded")).toBeInTheDocument();
    expect(screen.getByText("degradable")).toBeInTheDocument();
  });

  it("says plainly when automatic retention is not enforced", async () => {
    // An operator must not have to infer "0 days" means "off".
    mockedStatus.mockResolvedValue(healthy);

    renderSection();

    expect(await screen.findByText(/not enforced/)).toBeInTheDocument();
  });

  it("reports the configured retention when it is enforced", async () => {
    mockedStatus.mockResolvedValue({
      ...healthy,
      retentionDays: 90,
      retentionEnforced: true,
      investigationsErased: 4,
    });

    renderSection();

    expect(
      await screen.findByText(/erased automatically after/),
    ).toBeInTheDocument();
    expect(screen.getByText(/4 erased by policy/)).toBeInTheDocument();
  });

  it("warns when the audit sink is not durable", async () => {
    mockedStatus.mockResolvedValue({
      ...healthy,
      auditSink: "log",
      auditDurable: false,
    });

    renderSection();

    expect(await screen.findByText(/log-only/)).toBeInTheDocument();
  });

  it("raises an alert when audit records could not be stored", async () => {
    // An unrecorded action is an accountability gap; it must be loud here too.
    mockedStatus.mockResolvedValue({ ...healthy, auditWriteFailures: 3 });

    renderSection();

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "3 audit records could not be stored",
    );
  });

  it("surfaces a load failure with a retry", async () => {
    mockedStatus.mockRejectedValue(new Error("boom"));

    renderSection();

    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Retry" }),
    ).toBeInTheDocument();
  });
});
