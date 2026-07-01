import { afterEach, describe, expect, it, vi } from "vitest";
import { apiClient, setAuthTokenSource } from "./apiClient";
import { ApiError } from "./errors";

interface FetchResult {
  readonly ok: boolean;
  readonly status: number;
  readonly body: unknown;
}

function mockFetch(result: FetchResult) {
  const fetchMock = vi.fn(
    (_input: RequestInfo | URL, _init?: RequestInit) =>
      Promise.resolve({
        ok: result.ok,
        status: result.status,
        json: () => Promise.resolve(result.body),
      } as unknown as Response),
  );
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

const META = {
  request_id: "req-1",
  correlation_id: "req-1",
  timestamp: "2026-06-30T00:00:00Z",
  api_version: "v1",
};

afterEach(() => {
  vi.unstubAllGlobals();
  setAuthTokenSource(() => null);
});

describe("apiClient", () => {
  it("unwraps the success envelope and returns data", async () => {
    mockFetch({
      ok: true,
      status: 200,
      body: { status: "success", data: { id: "inv-1" }, meta: META },
    });
    const data = await apiClient.get<{ id: string }>("/api/v1/investigations/inv-1");
    expect(data).toEqual({ id: "inv-1" });
  });

  it("maps the error envelope to an ApiError", async () => {
    mockFetch({
      ok: false,
      status: 404,
      body: {
        status: "error",
        error: { code: "investigation.not_found", message: "not found" },
        meta: META,
      },
    });
    await expect(apiClient.get("/api/v1/investigations/nope")).rejects.toMatchObject({
      code: "investigation.not_found",
      message: "not found",
      status: 404,
      requestId: "req-1",
    });
  });

  it("sends the method and body for post", async () => {
    const fetchMock = mockFetch({
      ok: true,
      status: 201,
      body: { status: "success", data: { id: "inv-1" }, meta: META },
    });
    await apiClient.post("/api/v1/investigations", { title: "Phish" });
    const init = fetchMock.mock.calls[0]![1]!;
    expect(init).toMatchObject({
      method: "POST",
      body: JSON.stringify({ title: "Phish" }),
    });
  });

  it("attaches the Authorization header from the token source", async () => {
    setAuthTokenSource(() => "token-123");
    const fetchMock = mockFetch({
      ok: true,
      status: 200,
      body: { status: "success", data: null, meta: META },
    });
    await apiClient.get("/api/v1/investigations/inv-1");
    const init = fetchMock.mock.calls[0]![1]!;
    const headers = init.headers as Record<string, string>;
    expect(headers.Authorization).toBe("Bearer token-123");
  });

  it("produces an immutable ApiError", () => {
    const error = new ApiError("x.y", "msg", 400, "req-1");
    expect(Object.isFrozen(error)).toBe(true);
  });
});
