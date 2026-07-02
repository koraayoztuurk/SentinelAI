// Architecture test (ES-033).
//
// Independently verifies a frontend architectural boundary (Architecture Validation,
// testing-strategy §5): the Communication layer is the single Backend API boundary
// (Frontend Architecture §10), so `fetch` must only appear inside `communication/`.
// The source is scanned at build time via Vite's `import.meta.glob`.

import { describe, expect, it } from "vitest";

const sources = import.meta.glob("./**/*.{ts,tsx}", {
  query: "?raw",
  eager: true,
  import: "default",
}) as Record<string, string>;

function isProductionSource(path: string): boolean {
  return (
    !path.includes(".test.") &&
    !path.includes("/mocks/") &&
    !path.includes("/test/")
  );
}

describe("frontend architecture", () => {
  it("calls fetch only from the communication layer", () => {
    const offenders = Object.entries(sources)
      .filter(([path]) => isProductionSource(path))
      .filter(([path, source]) => /\bfetch\s*\(/.test(source) && !path.includes("/communication/"))
      .map(([path]) => path);

    expect(offenders).toEqual([]);
  });
});
