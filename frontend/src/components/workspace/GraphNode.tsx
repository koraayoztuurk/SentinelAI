// Graph node component (SVG).
//
// Renders a single positioned entity as a pill carrying its own name. The seed
// (exploration origin) and the focused node are emphasized. Selecting a node
// drives the drill-down re-centering through the shared Investigation Context.
// This component only renders — positions, sizes and labels are computed by the
// pure layout helpers.
//
// Two deliberate properties:
//
// - **The name is inside the node.** A circle with a caption underneath needs
//   room for the caption, and captions of adjacent nodes overlap as soon as the
//   neighbourhood grows. A pill carries its label in space it already occupies.
// - **It is keyboard operable.** The node is a real focus stop (`tabindex`) that
//   responds to Enter and Space, so drilling through a graph never requires a
//   mouse. An SVG `role="button"` that only listens for clicks is a trap.

import {
  entityTone,
  nodeLabel,
  type EntityTone,
  type PositionedNode,
} from "../../communication/graph";

export interface GraphNodeProps {
  readonly node: PositionedNode;
  readonly focused: boolean;
  readonly onSelect: (entityId: string) => void;
}

const TONE_VAR: Record<EntityTone, string> = {
  cyan: "var(--color-cyan)",
  lav: "var(--color-lav)",
  mint: "var(--color-mint)",
  amber: "var(--color-amber)",
  coral: "var(--color-coral)",
  neutral: "var(--color-ink-3)",
};

export function GraphNode({ node, focused, onSelect }: GraphNodeProps) {
  const tone = TONE_VAR[entityTone(node.type)];
  const label = nodeLabel(node);
  const x = node.x - node.width / 2;
  const y = node.y - node.height / 2;

  return (
    <g
      role="button"
      tabIndex={0}
      aria-pressed={focused}
      aria-label={`${label} — ${node.type || "entity"}${
        node.isSeed ? ", exploration origin" : ""
      }`}
      className="cursor-pointer"
      style={{ outlineOffset: "3px" }}
      onClick={() => onSelect(node.id)}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          onSelect(node.id);
        }
      }}
    >
      <title>{`${node.displayName} · ${node.type} · confidence ${Math.round(
        node.confidence * 100,
      )}%`}</title>

      <rect
        x={x}
        y={y}
        width={node.width}
        height={node.height}
        rx={node.height / 2}
        fill={focused ? tone : "var(--color-paper)"}
        fillOpacity={focused ? 0.22 : 1}
        stroke={focused ? tone : "var(--color-line-2)"}
        strokeWidth={focused ? 2 : 1.25}
        style={{ transition: "fill-opacity 180ms, stroke 180ms" }}
      />

      {/* Type dot: colour is the encoding, the tooltip and legend name it. */}
      <circle cx={x + 13} cy={node.y} r={4} fill={tone} />

      <text
        x={x + 24}
        y={node.y}
        dominantBaseline="central"
        fill="var(--color-ink)"
        className="font-mono text-[11px]"
        style={{ fontWeight: node.isSeed ? 600 : 400 }}
      >
        {label}
      </text>
    </g>
  );
}
