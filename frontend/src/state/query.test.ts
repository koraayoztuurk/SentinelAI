import { describe, expect, it, vi } from "vitest";
import {
  createQueryClient,
  dashboardQuery,
  entityNeighborhoodQuery,
  invalidateEntityNeighborhood,
  invalidateWorkspace,
  queryKeys,
  workspaceQuery,
} from "./query";

describe("queryKeys", () => {
  it("produces stable, namespaced keys", () => {
    expect(queryKeys.dashboard("inv-1")).toEqual(["dashboard", "inv-1"]);
    expect(queryKeys.workspace("inv-1")).toEqual(["workspace", "inv-1"]);
    expect(queryKeys.entityNeighborhood("host-12")).toEqual([
      "graph",
      "neighborhood",
      "host-12",
    ]);
  });
});

describe("query option builders", () => {
  it("carry the resource key", () => {
    expect(dashboardQuery("inv-1").queryKey).toEqual(["dashboard", "inv-1"]);
    expect(workspaceQuery("inv-1").queryKey).toEqual(["workspace", "inv-1"]);
  });

  it("gate the neighbourhood query on a non-null entity", () => {
    expect(entityNeighborhoodQuery(null).enabled).toBe(false);
    const enabled = entityNeighborhoodQuery("host-12");
    expect(enabled.enabled).toBe(true);
    expect(enabled.queryKey).toEqual(["graph", "neighborhood", "host-12"]);
  });
});

describe("invalidate helpers", () => {
  it("invalidate exactly the resource's key through the client", () => {
    const client = createQueryClient();
    const spy = vi.spyOn(client, "invalidateQueries").mockResolvedValue();

    void invalidateWorkspace(client, "inv-1");
    void invalidateEntityNeighborhood(client, "host-12");

    expect(spy).toHaveBeenCalledWith({ queryKey: ["workspace", "inv-1"] });
    expect(spy).toHaveBeenCalledWith({
      queryKey: ["graph", "neighborhood", "host-12"],
    });
  });
});
