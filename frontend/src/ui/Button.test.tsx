import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { Button } from "./Button";

describe("Button", () => {
  it("renders its children", () => {
    render(<Button>Run</Button>);
    expect(screen.getByRole("button", { name: "Run" })).toBeInTheDocument();
  });

  it("invokes onClick when clicked", async () => {
    const onClick = vi.fn();
    render(<Button onClick={onClick}>Run</Button>);
    await userEvent.click(screen.getByRole("button", { name: "Run" }));
    expect(onClick).toHaveBeenCalledOnce();
  });

  it("does not invoke onClick when disabled", async () => {
    const onClick = vi.fn();
    render(
      <Button onClick={onClick} disabled>
        Run
      </Button>,
    );
    await userEvent.click(screen.getByRole("button", { name: "Run" }));
    expect(onClick).not.toHaveBeenCalled();
  });
});
