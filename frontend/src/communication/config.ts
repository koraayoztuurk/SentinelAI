// Communication configuration.
//
// The Backend API base URL is read from the environment through a single
// accessor so that `import.meta.env` is never referenced throughout the rest of
// the application.
//
// The default is same-origin (empty base): in development the Vite dev server
// proxies `/api` and `/health` to the local backend (vite.config.ts), and in
// the containerized deployment nginx does the same — so the browser never
// needs CORS. A different origin can still be baked with `VITE_API_BASE_URL`
// (the production compose bakes the published origin).

const DEFAULT_BASE_URL = "";

export function getApiBaseUrl(): string {
  const configured = import.meta.env.VITE_API_BASE_URL;
  return configured && configured.length > 0 ? configured : DEFAULT_BASE_URL;
}
