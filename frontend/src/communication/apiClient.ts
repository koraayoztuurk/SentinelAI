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

function authHeader(): Record<string, string> {
  const token = getAuthToken();
  return token !== null ? { Authorization: `Bearer ${token}` } : {};
}

// Run a fetch under the shared timeout + cancellation discipline, mapping an
// unreachable backend to the same stable error every caller expects.
async function send(
  path: string,
  init: RequestInit,
  signal: AbortSignal | undefined,
  timeoutMs: number,
): Promise<Response> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  if (signal) {
    signal.addEventListener("abort", () => controller.abort(), { once: true });
  }
  try {
    return await fetch(`${getApiBaseUrl()}${path}`, {
      ...init,
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
}

async function errorFrom(response: Response): Promise<ApiError> {
  const payload = (await response.json().catch(() => null)) as
    | ApiErrorResponse
    | null;
  return new ApiError(
    payload?.error.code ?? "communication.error",
    payload?.error.message ?? "The request failed.",
    response.status,
    payload?.meta.request_id ?? null,
  );
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, signal, timeoutMs = DEFAULT_TIMEOUT_MS } = options;

  const headers: Record<string, string> = {
    Accept: "application/json",
    ...authHeader(),
  };
  if (body !== undefined) {
    headers["Content-Type"] = "application/json";
  }

  const response = await send(
    path,
    { method, headers, body: body === undefined ? undefined : JSON.stringify(body) },
    signal,
    timeoutMs,
  );

  if (!response.ok) {
    throw await errorFrom(response);
  }
  const payload = (await response.json().catch(() => null)) as ApiSuccess<T> | null;
  return (payload as ApiSuccess<T>).data;
}

// Raw-bytes upload (evidence payloads, ES-061): sends an octet-stream body and
// unwraps the JSON success envelope like `request`. The payload never becomes a
// JSON document — api-design §8: payloads travel as byte streams.
async function postBinary<T>(
  path: string,
  bytes: ArrayBuffer,
  options: Omit<RequestOptions, "method" | "body"> = {},
): Promise<T> {
  const { signal, timeoutMs = DEFAULT_TIMEOUT_MS } = options;
  const response = await send(
    path,
    {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/octet-stream",
        ...authHeader(),
      },
      body: bytes,
    },
    signal,
    timeoutMs,
  );
  if (!response.ok) {
    throw await errorFrom(response);
  }
  const payload = (await response.json().catch(() => null)) as ApiSuccess<T> | null;
  return (payload as ApiSuccess<T>).data;
}

// Raw-bytes download (verified evidence payloads, ES-061): the response is the
// bytes themselves, not an envelope; an error response still carries the JSON
// error envelope.
async function getBlob(
  path: string,
  options: Omit<RequestOptions, "method" | "body"> = {},
): Promise<Blob> {
  const { signal, timeoutMs = DEFAULT_TIMEOUT_MS } = options;
  const response = await send(
    path,
    { method: "GET", headers: { ...authHeader() } },
    signal,
    timeoutMs,
  );
  if (!response.ok) {
    throw await errorFrom(response);
  }
  return response.blob();
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
  postBinary,
  getBlob,
};
