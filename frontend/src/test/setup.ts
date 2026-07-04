// Vitest setup: jest-dom matchers.
//
// The app talks to the real backend since ES-047 (no browser mocking layer);
// tests mock the communication loaders directly, and the mapper tests reuse
// the shared sample data (`src/mocks/data.ts`) without the network.

import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

// Unmount and clear the DOM after every test. React Testing Library's automatic
// cleanup is not reliably registered on this runtime, so a rendered tree could
// otherwise leak into the next test (producing duplicate-element matches). Session
// State persists to localStorage (ES-027), so clear it too to keep the theme
// preference from leaking across tests.
afterEach(() => {
  cleanup();
  // Best-effort: localStorage is not fully implemented on every test runtime.
  try {
    localStorage.clear();
  } catch {
    /* localStorage may be unavailable — the Session State store degrades the same way. */
  }
});
