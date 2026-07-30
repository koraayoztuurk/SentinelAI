import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { ThemeToggle } from "./ThemeToggle";
import { SessionProvider } from "../state/session";

function renderToggle() {
  return render(
    <SessionProvider>
      <ThemeToggle />
    </SessionProvider>,
  );
}

describe("ThemeToggle", () => {
  it("defaults to light and toggles to dark, applying the DOM attribute", async () => {
    renderToggle();
    const button = screen.getByRole("button");
    expect(button).toHaveTextContent("Theme: light");

    await userEvent.click(button);

    expect(button).toHaveTextContent("Theme: dark");
    expect(document.documentElement.getAttribute("data-theme")).toBe("dark");
  });
});
