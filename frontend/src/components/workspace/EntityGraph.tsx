// Entity graph component (SVG ego-graph).
//
// Renders the seed entity and its neighbourhood as a node-link diagram. All geometry
// comes from the pure layout helpers (`calculateNodePositions` /
// `calculateEdgeGeometry`) — this component only draws the result (compute→render
// separation). Nodes are clickable to drill down; edges are directed (arrow marker)
// and labelled with the relationship type.

import {
  DEFAULT_GRAPH_LAYOUT,
  calculateEdgeGeometry,
  calculateNodePositions,
  type GraphViewModel,
} from "../../communication/graph";
import { GraphNode } from "./GraphNode";

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
  const nodes = calculateNodePositions(graph);
  const edges = calculateEdgeGeometry(nodes, graph.edges);
  const { width, height } = DEFAULT_GRAPH_LAYOUT;

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      className="h-auto w-full"
      role="img"
      aria-label="Entity neighbourhood graph"
    >
      <defs>
        <marker
          id="graph-arrow"
          viewBox="0 0 10 10"
          refX="9"
          refY="5"
          markerWidth="6"
          markerHeight="6"
          orient="auto-start-reverse"
        >
          <path d="M 0 0 L 10 5 L 0 10 z" className="fill-white/40" />
        </marker>
      </defs>

      {edges.map((edge) => (
        <g key={edge.id}>
          <line
            x1={edge.x1}
            y1={edge.y1}
            x2={edge.x2}
            y2={edge.y2}
            className="stroke-white/30"
            strokeWidth={1}
            markerEnd="url(#graph-arrow)"
          />
          <text
            x={edge.midX}
            y={edge.midY}
            textAnchor="middle"
            className="fill-white/50 text-[9px]"
          >
            {edge.type}
          </text>
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
