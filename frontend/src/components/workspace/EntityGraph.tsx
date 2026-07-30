// Entity graph component (SVG ego-graph).
//
// Renders the seed entity and its neighbourhood as a node-link diagram. All
// geometry comes from the pure layout helpers (`layoutFor` /
// `calculateNodePositions` / `calculateEdgeGeometry`) — this component only
// draws the result (compute→render separation).
//
// Three things this drawing gets right that the first version did not:
//
// - **Edges stop at the node boundary**, so the arrowhead is visible and the
//   relationship's direction can actually be read. Drawn centre-to-centre, every
//   arrow was hidden underneath the node it pointed at.
// - **The canvas grows with the neighbourhood.** A fixed viewBox meant a dense
//   graph stacked its nodes on top of each other.
// - **Relationship labels sit on a plate**, so the type is readable where an
//   edge crosses another edge. Past a threshold they are dropped rather than
//   turned into noise — the type stays available on hover and in the list below.

import {
  calculateEdgeGeometry,
  calculateNodePositions,
  layoutFor,
  type GraphViewModel,
} from "../../communication/graph";
import { GraphNode } from "./GraphNode";

// Above this many edges, per-edge labels overlap more than they inform.
const EDGE_LABEL_LIMIT = 8;

export interface EntityGraphProps {
  readonly graph: GraphViewModel;
  readonly focusedEntityId: string | null;
  readonly onSelectEntity: (entityId: string) => void;
}

export function EntityGraph({
  graph,
  focusedEntityId,
  onSelectEntity,
}: EntityGraphProps) {
  const neighbourCount = graph.nodes.filter((node) => !node.isSeed).length;
  const layout = layoutFor(neighbourCount);
  const nodes = calculateNodePositions(graph, layout);
  const edges = calculateEdgeGeometry(nodes, graph.edges);
  const showLabels = edges.length <= EDGE_LABEL_LIMIT;

  return (
    <svg
      viewBox={`0 0 ${layout.width} ${layout.height}`}
      className="rise h-auto w-full"
      role="img"
      aria-label={`Neighbourhood of ${graph.seedId}: ${neighbourCount} connected ${
        neighbourCount === 1 ? "entity" : "entities"
      }, ${edges.length} ${edges.length === 1 ? "relationship" : "relationships"}`}
    >
      <defs>
        <marker
          id="graph-arrow"
          viewBox="0 0 10 10"
          refX="8"
          refY="5"
          markerWidth="7"
          markerHeight="7"
          orient="auto-start-reverse"
        >
          <path d="M 0 0 L 10 5 L 0 10 z" fill="var(--color-line-2)" />
        </marker>
      </defs>

      {edges.map((edge) => (
        <g key={edge.id}>
          <title>{`${edge.source} —${edge.type}→ ${edge.target}`}</title>
          <line
            x1={edge.drawX1}
            y1={edge.drawY1}
            x2={edge.drawX2}
            y2={edge.drawY2}
            className="edge"
            markerEnd="url(#graph-arrow)"
          />
          {showLabels && (
            <>
              {/* A plate behind the type keeps it readable over other edges. */}
              <rect
                x={edge.midX - edge.type.length * 3.1 - 5}
                y={edge.midY - 8}
                width={edge.type.length * 6.2 + 10}
                height={16}
                rx={8}
                fill="var(--color-paper)"
                stroke="var(--color-line)"
                strokeWidth={1}
              />
              <text
                x={edge.midX}
                y={edge.midY}
                textAnchor="middle"
                dominantBaseline="central"
                fill="var(--color-ink-2)"
                className="font-mono text-[9px]"
              >
                {edge.type}
              </text>
            </>
          )}
        </g>
      ))}

      {nodes.map((node) => (
        <GraphNode
          key={node.id}
          node={node}
          focused={node.id === focusedEntityId}
          onSelect={onSelectEntity}
        />
      ))}
    </svg>
  );
}
