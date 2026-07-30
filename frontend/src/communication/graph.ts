// Graph data access + view model + layout.
//
// The Graph Visualization presents an entity and its neighbourhood as a node-link
// diagram (visualization-architecture §5). The backend Graph API is entity-seeded
// (there is no investigation→graph endpoint), so a graph is built from a seed
// entity: its neighbours (nodes) and its incident relationships (edges).
//
// The DTOs mirror the backend response shapes (ES-016); they stay internal to the
// communication layer — the UI consumes view models. Composition and geometry are
// pure and standalone (mirroring the ES-025 timeline helpers and the backend's
// compute→render separation): `toGraphViewModel` composes the graph,
// `calculateNodePositions` produces node coordinates and `calculateEdgeGeometry`
// produces edge line geometry. `EntityGraph` only renders the result.

import { apiClient } from "./apiClient";

export interface EntityDto {
  readonly id: string;
  readonly type: string;
  readonly display_name: string;
  readonly confidence: number;
  readonly source: string;
  readonly attributes: Record<string, string>;
  readonly aliases: readonly string[];
}

export interface RelationshipDto {
  readonly id: string;
  readonly source_entity_id: string;
  readonly target_entity_id: string;
  readonly type: string;
  readonly confidence: number;
  readonly supporting_evidence: readonly string[];
  readonly created_at: string;
}

// ------------------------------------------------------------------ data access

export function getEntity(
  entityId: string,
  signal?: AbortSignal,
): Promise<EntityDto> {
  return apiClient.get<EntityDto>(
    `/api/v1/graph/entities/${encodeURIComponent(entityId)}`,
    { signal },
  );
}

export function listEntityRelationships(
  entityId: string,
  signal?: AbortSignal,
): Promise<readonly RelationshipDto[]> {
  return apiClient.get<readonly RelationshipDto[]>(
    `/api/v1/graph/entities/${encodeURIComponent(entityId)}/relationships`,
    { signal },
  );
}

export function findNeighbors(
  entityId: string,
  depth: number,
  maxNodes: number,
  signal?: AbortSignal,
): Promise<readonly EntityDto[]> {
  return apiClient.get<readonly EntityDto[]>(
    `/api/v1/graph/entities/${encodeURIComponent(entityId)}/neighbors` +
      `?depth=${depth}&max_nodes=${maxNodes}`,
    { signal },
  );
}

// ------------------------------------------------------------------- view model

export interface GraphNodeViewModel {
  readonly id: string;
  readonly displayName: string;
  readonly type: string;
  readonly confidence: number;
  readonly isSeed: boolean;
}

export interface GraphEdgeViewModel {
  readonly id: string;
  readonly source: string;
  readonly target: string;
  readonly type: string;
  readonly confidence: number;
}

export interface GraphViewModel {
  readonly seedId: string;
  readonly nodes: readonly GraphNodeViewModel[];
  readonly edges: readonly GraphEdgeViewModel[];
}

function toNode(entity: EntityDto, isSeed: boolean): GraphNodeViewModel {
  return {
    id: entity.id,
    displayName: entity.display_name,
    type: entity.type,
    confidence: entity.confidence,
    isSeed,
  };
}

// Pure: compose the ego graph. Nodes are the seed plus its (deduplicated,
// id-ordered) neighbours; edges are the seed's relationships restricted to those
// whose endpoints are both present, so no edge dangles off the visible graph.
export function toGraphViewModel(
  seed: EntityDto,
  neighbours: readonly EntityDto[],
  relationships: readonly RelationshipDto[],
): GraphViewModel {
  const neighbourNodes = [...neighbours]
    .filter((entity) => entity.id !== seed.id)
    .sort((a, b) => a.id.localeCompare(b.id))
    .map((entity) => toNode(entity, false));
  const nodes = [toNode(seed, true), ...neighbourNodes];
  const nodeIds = new Set(nodes.map((node) => node.id));

  const edges = relationships
    .filter(
      (rel) =>
        nodeIds.has(rel.source_entity_id) &&
        nodeIds.has(rel.target_entity_id),
    )
    .map(
      (rel): GraphEdgeViewModel => ({
        id: rel.id,
        source: rel.source_entity_id,
        target: rel.target_entity_id,
        type: rel.type,
        confidence: rel.confidence,
      }),
    )
    .sort(
      (a, b) =>
        a.source.localeCompare(b.source) ||
        a.target.localeCompare(b.target) ||
        a.type.localeCompare(b.type),
    );

  return { seedId: seed.id, nodes, edges };
}

// -------------------------------------------------------------------- layout

export interface GraphLayoutOptions {
  readonly width: number;
  readonly height: number;
  readonly radius: number;
}

// Wider than tall: the region it draws into is a wide panel, and a 4:3 canvas
// scaled to that width became mostly empty vertical space.
export const DEFAULT_GRAPH_LAYOUT: GraphLayoutOptions = {
  width: 620,
  height: 380,
  radius: 140,
};

// A node is drawn as a pill carrying its own display name, rather than a circle
// with a caption underneath. Two reasons: the name is always legible, and there
// is no separate label to collide with a neighbour's label — the crowding that
// made the previous ego-graph unreadable past a handful of nodes.
const LABEL_CHAR_WIDTH = 6.7; // JetBrains Mono at 11px
const LABEL_PADDING = 30; // type dot + inner padding
const MIN_NODE_WIDTH = 74;
const MAX_NODE_WIDTH = 190;
const NODE_HEIGHT = 32;
const SEED_NODE_HEIGHT = 38;
const LABEL_LIMIT = 22;

/** Pure: the label a node shows, elided to keep pills a workable width. */
export function nodeLabel(node: GraphNodeViewModel): string {
  const name = node.displayName.trim() || node.id;
  return name.length > LABEL_LIMIT ? `${name.slice(0, LABEL_LIMIT - 1)}…` : name;
}

/** Pure: pill geometry for a node, derived from its elided label. */
export function nodeSize(node: GraphNodeViewModel): {
  readonly width: number;
  readonly height: number;
} {
  const estimated = nodeLabel(node).length * LABEL_CHAR_WIDTH + LABEL_PADDING;
  return {
    width: Math.min(MAX_NODE_WIDTH, Math.max(MIN_NODE_WIDTH, estimated)),
    height: node.isSeed ? SEED_NODE_HEIGHT : NODE_HEIGHT,
  };
}

/**
 * Pure: a layout sized for the neighbourhood it has to hold.
 *
 * The fixed 480×360 canvas worked for three neighbours and overlapped at ten.
 * The ring grows with the count and the canvas grows with the ring, so a dense
 * neighbourhood spreads instead of stacking. The default is returned unchanged
 * for small graphs, which keeps the documented default meaningful.
 */
export function layoutFor(neighbourCount: number): GraphLayoutOptions {
  if (neighbourCount <= 3) {
    return DEFAULT_GRAPH_LAYOUT;
  }
  // Enough arc per neighbour that pills clear each other at the ring.
  const radius = Math.min(300, Math.round((neighbourCount * 74) / (2 * Math.PI)) + 96);
  return {
    width: (radius + MAX_NODE_WIDTH / 2 + 16) * 2,
    height: (radius + NODE_HEIGHT + 20) * 2,
    radius,
  };
}

export interface PositionedNode extends GraphNodeViewModel {
  readonly x: number;
  readonly y: number;
  /** Pill width/height, so the renderer draws no geometry of its own. */
  readonly width: number;
  readonly height: number;
}

export interface PositionedEdge extends GraphEdgeViewModel {
  readonly x1: number;
  readonly y1: number;
  readonly x2: number;
  readonly y2: number;
  readonly midX: number;
  readonly midY: number;
  /**
   * The drawable segment: the centre-to-centre line trimmed back to each pill's
   * boundary. Without this the arrowhead lands *under* the target node and the
   * edge's direction — the whole point of drawing it — is invisible.
   */
  readonly drawX1: number;
  readonly drawY1: number;
  readonly drawX2: number;
  readonly drawY2: number;
}

// Pure: deterministic radial (ego) layout — the seed sits at the centre and the
// neighbours are distributed evenly on a circle around it, starting at the top.
export function calculateNodePositions(
  graph: GraphViewModel,
  options: GraphLayoutOptions = DEFAULT_GRAPH_LAYOUT,
): readonly PositionedNode[] {
  const centerX = options.width / 2;
  const centerY = options.height / 2;
  const neighbours = graph.nodes.filter((node) => !node.isSeed);

  return graph.nodes.map((node) => {
    const size = nodeSize(node);
    if (node.isSeed) {
      return { ...node, ...size, x: centerX, y: centerY };
    }
    const index = neighbours.indexOf(node);
    const angle = -Math.PI / 2 + (index * 2 * Math.PI) / neighbours.length;
    return {
      ...node,
      ...size,
      x: centerX + options.radius * Math.cos(angle),
      y: centerY + options.radius * Math.sin(angle),
    };
  });
}

// Pure: the distance from a pill's centre to its boundary along `angle`,
// approximating the rounded rectangle with its inscribing ellipse. Good enough
// for edge trimming and far simpler than a rect intersection.
function boundaryDistance(
  width: number,
  height: number,
  angle: number,
  margin: number,
): number {
  const rx = width / 2 + margin;
  const ry = height / 2 + margin;
  const cos = Math.cos(angle);
  const sin = Math.sin(angle);
  return (rx * ry) / Math.sqrt((ry * cos) ** 2 + (rx * sin) ** 2);
}

// Pure: resolve each edge to its endpoint coordinates using the positioned nodes.
// Edges whose endpoints are missing are dropped (defensive; `toGraphViewModel`
// already filters dangling edges).
export function calculateEdgeGeometry(
  positionedNodes: readonly PositionedNode[],
  edges: readonly GraphEdgeViewModel[],
): readonly PositionedEdge[] {
  const byId = new Map(positionedNodes.map((node) => [node.id, node]));
  const geometry: PositionedEdge[] = [];
  for (const edge of edges) {
    const source = byId.get(edge.source);
    const target = byId.get(edge.target);
    if (source === undefined || target === undefined) {
      continue;
    }
    const angle = Math.atan2(target.y - source.y, target.x - source.x);
    const fromCentre = boundaryDistance(source.width, source.height, angle, 2);
    const toCentre = boundaryDistance(target.width, target.height, angle, 6);
    geometry.push({
      ...edge,
      x1: source.x,
      y1: source.y,
      x2: target.x,
      y2: target.y,
      midX: (source.x + target.x) / 2,
      midY: (source.y + target.y) / 2,
      drawX1: source.x + Math.cos(angle) * fromCentre,
      drawY1: source.y + Math.sin(angle) * fromCentre,
      drawX2: target.x - Math.cos(angle) * toCentre,
      drawY2: target.y - Math.sin(angle) * toCentre,
    });
  }
  return geometry;
}

// ------------------------------------------------------------- type encoding

/**
 * Which accent carries which kind of entity.
 *
 * The vocabulary is an open string in the domain (entity types are not a closed
 * enum), so this is a presentation-side reading with an explicit fallback — an
 * unknown type renders neutrally rather than being dropped or mis-coloured.
 */
export type EntityTone = "cyan" | "lav" | "mint" | "amber" | "coral" | "neutral";

const TONE_BY_TYPE: Record<string, EntityTone> = {
  endpoint: "cyan",
  host: "cyan",
  server: "cyan",
  device: "cyan",
  ip: "amber",
  ip_address: "amber",
  domain: "amber",
  url: "amber",
  user: "lav",
  account: "lav",
  identity: "lav",
  process: "mint",
  file: "mint",
  service: "mint",
  malware: "coral",
  vulnerability: "coral",
  threat_actor: "coral",
};

export function entityTone(type: string): EntityTone {
  return TONE_BY_TYPE[type.trim().toLowerCase()] ?? "neutral";
}

/** Pure: the entity types present in a graph, in first-seen order (legend). */
export function graphLegend(
  graph: GraphViewModel,
): readonly { readonly type: string; readonly tone: EntityTone }[] {
  const seen = new Set<string>();
  const legend: { type: string; tone: EntityTone }[] = [];
  for (const node of graph.nodes) {
    const type = node.type.trim().toLowerCase();
    if (type !== "" && !seen.has(type)) {
      seen.add(type);
      legend.push({ type, tone: entityTone(type) });
    }
  }
  return legend;
}

// ----------------------------------------------------------------------- loader

const NEIGHBOURHOOD_DEPTH = 1;
const NEIGHBOURHOOD_MAX_NODES = 25;

export async function loadEntityNeighborhood(
  entityId: string,
  signal?: AbortSignal,
): Promise<GraphViewModel> {
  const [seed, relationships, neighbours] = await Promise.all([
    getEntity(entityId, signal),
    listEntityRelationships(entityId, signal),
    findNeighbors(entityId, NEIGHBOURHOOD_DEPTH, NEIGHBOURHOOD_MAX_NODES, signal),
  ]);
  return toGraphViewModel(seed, neighbours, relationships);
}
