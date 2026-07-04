import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it } from "vitest";
import { DevTokenField } from "./DevTokenField";
import {
  getDevAuthCredential,
  setDevAuthCredential,
} from "../state/devAuth";

describe("DevTokenField", () => {
  beforeEach(() => {
    setDevAuthCredential("");
  });

  it("stores the committed credential and shows the subject", async () => {
    render(<DevTokenField />);

    const input = screen.getByLabelText("Development credential");
    await userEvent.type(input, "alice:secret-1{Enter}");

    expect(getDevAuthCredential()).toBe("alice:secret-1");
    expect(screen.getByText("Signed in: alice")).toBeInTheDocument();
    // The committed value is never displayed back.
    expect(input).toHaveValue("");
  });

  it("prompts for a token when none is configured", () => {
    render(<DevTokenField />);
    expect(screen.getByText("Dev token")).toBeInTheDocument();
  });
});
