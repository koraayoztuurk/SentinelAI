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

export const DEFAULT_GRAPH_LAYOUT: GraphLayoutOptions = {
  width: 480,
  height: 360,
  radius: 140,
};

export interface PositionedNode extends GraphNodeViewModel {
  readonly x: number;
  readonly y: number;
}

export interface PositionedEdge extends GraphEdgeViewModel {
  readonly x1: number;
  readonly y1: number;
  readonly x2: number;
  readonly y2: number;
  readonly midX: number;
  readonly midY: number;
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
    if (node.isSeed) {
      return { ...node, x: centerX, y: centerY };
    }
    const index = neighbours.indexOf(node);
    const angle = -Math.PI / 2 + (index * 2 * Math.PI) / neighbours.length;
    return {
      ...node,
      x: centerX + options.radius * Math.cos(angle),
      y: centerY + options.radius * Math.sin(angle),
    };
  });
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
    geometry.push({
      ...edge,
      x1: source.x,
      y1: source.y,
      x2: target.x,
      y2: target.y,
      midX: (source.x + target.x) / 2,
      midY: (source.y + target.y) / 2,
    });
  }
  return geometry;
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
