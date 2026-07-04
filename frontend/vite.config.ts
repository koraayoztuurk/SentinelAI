import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// Vite configuration for the SentinelAI single-page application. The Vitest
// test configuration lives here so the test runner shares the app's resolution.
//
// The dev server proxies the backend paths to the locally running backend
// (same-origin, no CORS — mirroring the nginx reverse proxy of the
// containerized deployment), so `npm run dev` talks to the real API (ES-047).
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      "/api": "http://127.0.0.1:8000",
      "/health": "http://127.0.0.1:8000",
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    css: true,
    coverage: {
      provider: "v8",
      reporter: ["text", "html"],
      reportsDirectory: "coverage",
      include: ["src/**"],
    },
  },
});
