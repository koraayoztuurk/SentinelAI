import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { EvidenceSection } from "./EvidenceSection";
import { TestQueryProvider } from "../../test/TestQueryProvider";
import { WorkspaceProvider } from "../../state/workspaceContext";
import {
  attachEvidence,
  downloadEvidencePayload,
  uploadEvidencePayload,
} from "../../communication/investigations";
import type { EvidenceViewModel } from "../../communication/workspace";

vi.mock("../../communication/investigations", async (importOriginal) => {
  const actual =
    await importOriginal<typeof import("../../communication/investigations")>();
  return {
    ...actual,
    uploadEvidencePayload: vi.fn(),
    attachEvidence: vi.fn(),
    downloadEvidencePayload: vi.fn(),
  };
});

const mockedUpload = vi.mocked(uploadEvidencePayload);
const mockedAttach = vi.mocked(attachEvidence);
const mockedDownload = vi.mocked(downloadEvidencePayload);

const inlineEvidence: EvidenceViewModel = {
  id: "ev-inline",
  source: "edr",
  integrity: "verified",
  timestamp: "2026-07-17T09:20:00Z",
  content: "inline observation",
  downloadable: false,
};

const payloadEvidence: EvidenceViewModel = {
  id: "ev-payload",
  source: "upload",
  integrity: `sha256:${"a".repeat(64)}`,
  timestamp: "2026-07-17T09:25:00Z",
  content: "capture.pcap",
  downloadable: true,
};

function renderSection(
  evidence: readonly EvidenceViewModel[] = [inlineEvidence, payloadEvidence],
) {
  return render(
    <TestQueryProvider>
      <WorkspaceProvider>
        <EvidenceSection
          investigationId="inv-1"
          evidence={evidence}
          findingEvidence={{}}
        />
      </WorkspaceProvider>
    </TestQueryProvider>,
  );
}

describe("EvidenceSection payloads (ES-061)", () => {
  beforeEach(() => {
    mockedUpload.mockReset();
    mockedAttach.mockReset();
    mockedDownload.mockReset();
  });

  it("shows a download control only on downloadable evidence", () => {
    renderSection();
    // Two evidence cards, one downloadable payload.
    expect(screen.getAllByText("Download payload")).toHaveLength(1);
  });

  it("uploads a file then attaches evidence referencing its address", async () => {
    mockedUpload.mockResolvedValue({
      address: `sha256:${"b".repeat(64)}`,
      size_bytes: 12,
    });
    mockedAttach.mockResolvedValue({
      id: "ev-new",
      investigation_id: "inv-1",
      source: "upload",
      timestamp: "2026-07-17T10:00:00Z",
      integrity: `sha256:${"b".repeat(64)}`,
      content: "log.txt",
    });
    renderSection([]);

    await userEvent.type(
      screen.getByLabelText("Payload evidence source"),
      "upload",
    );
    const file = new File(["raw log bytes"], "log.txt", {
      type: "text/plain",
    });
    // jsdom's File lacks arrayBuffer(); the hook reads the picked file's bytes.
    Object.defineProperty(file, "arrayBuffer", {
      value: vi.fn().mockResolvedValue(new ArrayBuffer(13)),
    });
    await userEvent.upload(
      screen.getByLabelText("Evidence payload file"),
      file,
    );
    await userEvent.click(screen.getByRole("button", { name: "Upload file" }));

    await waitFor(() => expect(mockedUpload).toHaveBeenCalledTimes(1));
    expect(mockedUpload.mock.calls[0]?.[0]).toBe("inv-1");
    await waitFor(() => expect(mockedAttach).toHaveBeenCalledTimes(1));
    expect(mockedAttach.mock.calls[0]?.[1]).toEqual({
      source: "upload",
      integrity: `sha256:${"b".repeat(64)}`,
      content: "log.txt",
    });
  });

  it("downloads a payload through the authenticated boundary", async () => {
    mockedDownload.mockResolvedValue(new Blob(["bytes"]));
    // jsdom lacks object-URL + anchor.click plumbing; provide them.
    URL.createObjectURL = vi.fn(() => "blob:mock");
    URL.revokeObjectURL = vi.fn();
    const click = vi
      .spyOn(HTMLAnchorElement.prototype, "click")
      .mockImplementation(() => undefined);
    renderSection();

    await userEvent.click(screen.getByText("Download payload"));

    await waitFor(() => expect(mockedDownload).toHaveBeenCalledTimes(1));
    expect(mockedDownload).toHaveBeenCalledWith("inv-1", "ev-payload");
    expect(click).toHaveBeenCalled();

    click.mockRestore();
  });
});
