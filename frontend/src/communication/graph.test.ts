import { describe, expect, it } from "vitest";
import {
  DEFAULT_GRAPH_LAYOUT,
  calculateEdgeGeometry,
  calculateNodePositions,
  toGraphViewModel,
} from "./graph";
import { sampleEntities, sampleRelationships } from "../mocks/data";

const seed = sampleEntities.find((e) => e.id === "host-12")!;
const host19 = sampleEntities.find((e) => e.id === "host-19")!;
const jdoe = sampleEntities.find((e) => e.id === "user-jdoe")!;

describe("toGraphViewModel", () => {
  it("puts the seed first and orders neighbours by id", () => {
    const graph = toGraphViewModel(seed, [jdoe, host19], sampleRelationships);
    expect(graph.seedId).toBe("host-12");
    expect(graph.nodes.map((n) => n.id)).toEqual([
      "host-12",
      "host-19",
      "user-jdoe",
    ]);
    expect(graph.nodes[0]?.isSeed).toBe(true);
    expect(graph.nodes[1]?.isSeed).toBe(false);
  });

  it("keeps only edges whose endpoints are both present", () => {
    // sampleRelationships includes rel-3/rel-4 that dangle off this neighbourhood.
    const graph = toGraphViewModel(seed, [host19, jdoe], sampleRelationships);
    expect(graph.edges.map((e) => e.id)).toEqual(["rel-1", "rel-2"]);
  });

  it("excludes the seed if it also appears in the neighbours", () => {
    const graph = toGraphViewModel(seed, [seed, host19], sampleRelationships);
    expect(graph.nodes.filter((n) => n.id === "host-12")).toHaveLength(1);
  });
});

describe("calculateNodePositions", () => {
  it("centres the seed and spreads neighbours deterministically", () => {
    const graph = toGraphViewModel(seed, [host19, jdoe], sampleRelationships);
    const positions = calculateNodePositions(graph);
    const seedPos = positions.find((n) => n.isSeed)!;
    expect(seedPos.x).toBeCloseTo(DEFAULT_GRAPH_LAYOUT.width / 2);
    expect(seedPos.y).toBeCloseTo(DEFAULT_GRAPH_LAYOUT.height / 2);
    // First neighbour starts at the top (angle -90°).
    const first = positions.find((n) => n.id === "host-19")!;
    expect(first.x).toBeCloseTo(DEFAULT_GRAPH_LAYOUT.width / 2);
    expect(first.y).toBeCloseTo(
      DEFAULT_GRAPH_LAYOUT.height / 2 - DEFAULT_GRAPH_LAYOUT.radius,
    );
  });
});

describe("calculateEdgeGeometry", () => {
  it("resolves each edge to its endpoint coordinates", () => {
    const graph = toGraphViewModel(seed, [host19, jdoe], sampleRelationships);
    const positions = calculateNodePositions(graph);
    const geometry = calculateEdgeGeometry(positions, graph.edges);
    const rel1 = geometry.find((e) => e.id === "rel-1")!;
    const source = positions.find((n) => n.id === "host-12")!;
    const target = positions.find((n) => n.id === "host-19")!;
    expect([rel1.x1, rel1.y1]).toEqual([source.x, source.y]);
    expect([rel1.x2, rel1.y2]).toEqual([target.x, target.y]);
  });
});
