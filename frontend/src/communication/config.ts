// Communication configuration.
//
// The Backend API base URL is read from the environment through a single
// accessor so that `import.meta.env` is never referenced throughout the rest of
// the application.

const DEFAULT_BASE_URL = "http://localhost:8000";

export function getApiBaseUrl(): string {
  const configured = import.meta.env.VITE_API_BASE_URL;
  return configured && configured.length > 0 ? configured : DEFAULT_BASE_URL;
}
