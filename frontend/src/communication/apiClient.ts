// API client — the single communication boundary to the Backend API.
//
// Following the Frontend Architecture (§10), every backend request flows through
// this client so authentication, error translation and timeout handling stay
// centralized and consistent. UI components never call `fetch` directly and never
// manage authentication themselves.
//
// The client is stateless: it resolves the base URL through `getApiBaseUrl`,
// attaches the `Authorization` header from a pluggable token source, applies a
// request timeout, unwraps the backend success envelope to return `data`, and
// maps the error envelope to an immutable `ApiError`. The concrete authentication
// flow / token storage and a server-state cache library are deferred (ES-027).

import { getApiBaseUrl } from "./config";
import { ApiError } from "./errors";
import type { ApiErrorResponse, ApiSuccess } from "./types";

const DEFAULT_TIMEOUT_MS = 15_000;

export type AuthTokenSource = () => string | null;

let getAuthToken: AuthTokenSource = () => null;

/** Register the source the client reads the bearer token from. */
export function setAuthTokenSource(source: AuthTokenSource): void {
  getAuthToken = source;
}

export interface RequestOptions {
  readonly method?: string;
  readonly body?: unknown;
  readonly signal?: AbortSignal;
  readonly timeoutMs?: number;
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, signal, timeoutMs = DEFAULT_TIMEOUT_MS } = options;

  const headers: Record<string, string> = { Accept: "application/json" };
  const token = getAuthToken();
  if (token !== null) {
    headers.Authorization = `Bearer ${token}`;
  }
  if (body !== undefined) {
    headers["Content-Type"] = "application/json";
  }

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  if (signal) {
    signal.addEventListener("abort", () => controller.abort(), { once: true });
  }

  let response: Response;
  try {
    response = await fetch(`${getApiBaseUrl()}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: controller.signal,
    });
  } catch {
    throw new ApiError(
      "communication.unreachable",
      "The backend could not be reached.",
      0,
    );
  } finally {
    clearTimeout(timeout);
  }

  const payload: unknown = await response.json().catch(() => null);

  if (!response.ok) {
    const error = payload as ApiErrorResponse | null;
    throw new ApiError(
      error?.error.code ?? "communication.error",
      error?.error.message ?? "The request failed.",
      response.status,
      error?.meta.request_id ?? null,
    );
  }

  return (payload as ApiSuccess<T>).data;
}

export const apiClient = {
  request,
  get: <T>(path: string, options?: Omit<RequestOptions, "method" | "body">) =>
    request<T>(path, { ...options, method: "GET" }),
  post: <T>(path: string, body?: unknown, options?: Omit<RequestOptions, "method" | "body">) =>
    request<T>(path, { ...options, method: "POST", body }),
  put: <T>(path: string, body?: unknown, options?: Omit<RequestOptions, "method" | "body">) =>
    request<T>(path, { ...options, method: "PUT", body }),
  delete: <T>(path: string, options?: Omit<RequestOptions, "method" | "body">) =>
    request<T>(path, { ...options, method: "DELETE" }),
};
