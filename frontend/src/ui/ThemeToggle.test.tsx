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
  it("defaults to dark and toggles to light, applying the DOM attribute", async () => {
    renderToggle();
    const button = screen.getByRole("button");
    expect(button).toHaveTextContent("Theme: dark");

    await userEvent.click(button);

    expect(button).toHaveTextContent("Theme: light");
    expect(document.documentElement.getAttribute("data-theme")).toBe("light");
  });
});
