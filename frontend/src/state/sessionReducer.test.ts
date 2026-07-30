import { describe, expect, it } from "vitest";
import { defaultSessionState, sessionReducer } from "./sessionReducer";

describe("sessionReducer", () => {
  it("sets an explicit theme", () => {
    const next = sessionReducer(defaultSessionState, {
      type: "SET_THEME",
      theme: "light",
    });
    expect(next.theme).toBe("light");
  });

  it("defaults to the light console", () => {
    expect(defaultSessionState.theme).toBe("light");
  });

  it("toggles between light and dark", () => {
    const dark = sessionReducer(defaultSessionState, { type: "TOGGLE_THEME" });
    expect(dark.theme).toBe("dark");
    const light = sessionReducer(dark, { type: "TOGGLE_THEME" });
    expect(light.theme).toBe("light");
  });
});
