import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ConfidenceIndicator } from "./ConfidenceIndicator";
import { StatusBadge } from "./StatusBadge";

describe("ConfidenceIndicator", () => {
  it("renders the confidence as a percentage", () => {
    render(<ConfidenceIndicator value={0.86} />);
    expect(screen.getByText("86%")).toBeInTheDocument();
  });

  it("clamps out-of-range values", () => {
    render(<ConfidenceIndicator value={1.5} />);
    expect(screen.getByText("100%")).toBeInTheDocument();
  });
});

describe("StatusBadge", () => {
  it("renders the status label", () => {
    render(<StatusBadge status="validated" />);
    expect(screen.getByText("validated")).toBeInTheDocument();
  });
});
