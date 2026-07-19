// Graph node component (SVG).
//
// Renders a single positioned entity as a clickable circle with a label. The seed
// (exploration origin) and the focused node are emphasized — the focused node gets
// a breathing glow halo. Selecting a node drives the drill-down re-centering
// through the shared Investigation Context. This component only renders —
// positions are computed by the pure layout helpers.

import type { PositionedNode } from "../../communication/graph";

export interface GraphNodeProps {
  readonly node: PositionedNode;
  readonly focused: boolean;
  readonly onSelect: (entityId: string) => void;
}

export function GraphNode({ node, focused, onSelect }: GraphNodeProps) {
  const radius = node.isSeed ? 26 : 20;
  const fill = focused
    ? "fill-accent"
    : node.isSeed
      ? "fill-raise"
      : "fill-panel-2";
  return (
    <g
      role="button"
      aria-pressed={focused}
      className="group cursor-pointer"
      onClick={() => onSelect(node.id)}
    >
      <title>{`${node.displayName} (${node.type})`}</title>
      {focused && (
        <circle
          cx={node.x}
          cy={node.y}
          r={radius + 14}
          fill="url(#graph-node-glow)"
          className="glow-breathe"
        />
      )}
      <circle
        cx={node.x}
        cy={node.y}
        r={radius}
        className={`${fill} transition-all duration-200 group-hover:stroke-accent ${
          focused ? "stroke-accent" : "stroke-line-strong"
        }`}
        strokeWidth={focused ? 1.5 : 1}
      />
      <text
        x={node.x}
        y={node.y + radius + 12}
        textAnchor="middle"
        className={`font-mono text-[10px] ${focused ? "fill-ink" : "fill-muted"}`}
      >
        {node.displayName}
      </text>
    </g>
  );
}
