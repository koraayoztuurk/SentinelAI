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

  it("toggles between dark and light", () => {
    const light = sessionReducer(defaultSessionState, { type: "TOGGLE_THEME" });
    expect(light.theme).toBe("light");
    const dark = sessionReducer(light, { type: "TOGGLE_THEME" });
    expect(dark.theme).toBe("dark");
  });
});
