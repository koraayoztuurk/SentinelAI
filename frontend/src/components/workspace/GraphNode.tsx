// Graph node component (SVG).
//
// Renders a single positioned entity as a clickable circle with a label. The seed
// (exploration origin) and the focused node are emphasized. Selecting a node drives
// the drill-down re-centering through the shared Investigation Context. This
// component only renders — positions are computed by the pure layout helpers.

import type { PositionedNode } from "../../communication/graph";

export interface GraphNodeProps {
  readonly node: PositionedNode;
  readonly focused: boolean;
  readonly onSelect: (entityId: string) => void;
}

export function GraphNode({ node, focused, onSelect }: GraphNodeProps) {
  const radius = node.isSeed ? 26 : 20;
  const fill = focused
    ? "fill-[var(--color-accent)]"
    : node.isSeed
      ? "fill-white/25"
      : "fill-white/10";
  return (
    <g
      role="button"
      aria-pressed={focused}
      className="cursor-pointer"
      onClick={() => onSelect(node.id)}
    >
      <title>{`${node.displayName} (${node.type})`}</title>
      <circle
        cx={node.x}
        cy={node.y}
        r={radius}
        className={`${fill} stroke-white/40`}
        strokeWidth={1}
      />
      <text
        x={node.x}
        y={node.y + radius + 12}
        textAnchor="middle"
        className="fill-white text-[10px]"
      >
        {node.displayName}
      </text>
    </g>
  );
}
