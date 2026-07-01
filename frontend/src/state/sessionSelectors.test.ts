import { describe, expect, it } from "vitest";
import { selectIsDark, selectIsLight, selectTheme } from "./sessionSelectors";

describe("session selectors", () => {
  it("read the theme and its variants", () => {
    expect(selectTheme({ theme: "light" })).toBe("light");
    expect(selectIsLight({ theme: "light" })).toBe(true);
    expect(selectIsDark({ theme: "light" })).toBe(false);
    expect(selectIsDark({ theme: "dark" })).toBe(true);
  });
});
