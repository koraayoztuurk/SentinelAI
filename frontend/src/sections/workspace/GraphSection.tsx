// Graph region (visualization-architecture §5, investigation-workspace §5).
//
// The Graph Visualization region of the Investigation Workspace. It is entity-seeded
// (the backend Graph API has no investigation→graph endpoint): the seeds are the
// entities referenced by the confirmed findings. Selecting a seed starts the
// exploration (and highlights the active seed); the focused entity's neighbourhood
// is loaded and drawn as an SVG ego-graph. Clicking a node drills down by moving the
// focus, preserving the origin seed. All coordination flows through the shared
// Investigation Context — regions never talk to each other directly.
//
// The region carries what a bare node-link diagram cannot: a legend naming the
// colour encoding, a readout of the entity currently in focus, and a way back to
// the seed after drilling. A picture whose colours are unexplained is decoration.

import {
  entityTone,
  graphLegend,
  type EntityTone,
  type GraphViewModel,
} from "../../communication/graph";
import { Button } from "../../ui/Button";
import { useWorkspaceContext } from "../../state/workspaceContext";
import { useEntityNeighborhood } from "../../state/useEntityNeighborhood";
import { EntitySeedChip } from "../../components/workspace/EntitySeedChip";
import { EntityGraph } from "../../components/workspace/EntityGraph";
import { Empty } from "../../ui/Region";
import { WorkspaceRegion } from "./WorkspaceRegion";

const NOTE =
  "The people, machines and addresses this investigation touches, and how they connect. Start from one and step outward.";

const TONE_CLASS: Record<EntityTone, string> = {
  cyan: "bg-cyan",
  lav: "bg-lav",
  mint: "bg-mint",
  amber: "bg-amber",
  coral: "bg-coral",
  neutral: "bg-ink-3",
};

export interface GraphSectionProps {
  readonly seedEntities: readonly string[];
}

function Legend({ graph }: { readonly graph: GraphViewModel }) {
  const legend = graphLegend(graph);
  if (legend.length === 0) {
    return null;
  }
  return (
    <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-2">
      <span className="mono-label uppercase text-ink-3">In this graph</span>
      <ul className="flex flex-wrap items-center gap-x-4 gap-y-2">
        {legend.map((item) => (
          <li key={item.type} className="flex items-center gap-1.5">
            <span
              aria-hidden="true"
              className={`h-2 w-2 shrink-0 rounded-pill ${TONE_CLASS[item.tone]}`}
            />
            <span className="mono-label text-ink-2">{item.type}</span>
          </li>
        ))}
      </ul>
      {/* Colour groups related kinds — an address and a domain share one, a
          machine and a server share another. It is a category, not a type id. */}
      <span className="text-xs text-ink-3">
        colour groups related kinds of entity
      </span>
    </div>
  );
}

function FocusReadout({
  graph,
  focusedEntityId,
}: {
  readonly graph: GraphViewModel;
  readonly focusedEntityId: string | null;
}) {
  const node = graph.nodes.find((candidate) => candidate.id === focusedEntityId);
  if (node === undefined) {
    return null;
  }
  const tone = entityTone(node.type);
  return (
    <dl className="mt-3 flex flex-wrap items-baseline gap-x-5 gap-y-1.5">
      {/* The identifier, not the display name: the picture already carries the
          name, and the id is what you need to look this entity up elsewhere. */}
      <div className="flex min-w-0 items-baseline gap-2">
        <dt className="mono-label uppercase text-ink-3">In focus</dt>
        <dd className="flex min-w-0 items-center gap-1.5">
          <span
            aria-hidden="true"
            className={`h-2 w-2 shrink-0 rounded-pill ${TONE_CLASS[tone]}`}
          />
          <span className="mono-label truncate font-semibold text-ink">
            {node.id}
          </span>
        </dd>
      </div>
      <div className="flex items-baseline gap-2">
        <dt className="mono-label uppercase text-ink-3">Type</dt>
        <dd className="mono-label text-ink-2">{node.type || "—"}</dd>
      </div>
      <div className="flex items-baseline gap-2">
        <dt className="mono-label uppercase text-ink-3">Confidence</dt>
        <dd className="mono-label tabular-nums text-ink-2">
          {Math.round(node.confidence * 100)}%
        </dd>
      </div>
    </dl>
  );
}

export function GraphSection({ seedEntities }: GraphSectionProps) {
  const { state, dispatch } = useWorkspaceContext();
  const { graph, loading, error, retry } = useEntityNeighborhood(
    state.selectedEntityId,
  );

  if (seedEntities.length === 0) {
    return (
      <WorkspaceRegion title="Graph" note={NOTE}>
        <Empty>No entities to explore yet.</Empty>
      </WorkspaceRegion>
    );
  }

  // The seed to return to after drilling, or null when there is nothing to go
  // back to. Resolving it to a value (rather than a boolean flag) is what lets
  // the type narrow inside the callback below.
  const backToSeed =
    state.selectedSeedEntityId !== null &&
    state.selectedEntityId !== null &&
    state.selectedEntityId !== state.selectedSeedEntityId
      ? state.selectedSeedEntityId
      : null;

  return (
    <WorkspaceRegion title="Graph" note={NOTE}>
      <div className="flex flex-wrap items-center gap-2">
        {seedEntities.map((entityId) => (
          <EntitySeedChip
            key={entityId}
            entityId={entityId}
            active={state.selectedSeedEntityId === entityId}
            onSelect={(id) =>
              dispatch({ type: "SELECT_SEED_ENTITY", entityId: id })
            }
          />
        ))}
        {backToSeed !== null && (
          <Button
            variant="link"
            className="mono-label ml-1"
            onClick={() =>
              dispatch({ type: "SELECT_ENTITY", entityId: backToSeed })
            }
          >
            ← back to {backToSeed}
          </Button>
        )}
      </div>

      <div className="mt-4">
        {state.selectedEntityId === null && (
          <Empty>Select an entity above to draw its neighbourhood.</Empty>
        )}

        {loading && (
          <div role="status" className="grid gap-2">
            <span className="sr-only">Loading graph…</span>
            <div className="skeleton h-64 w-full" aria-hidden="true" />
          </div>
        )}

        {error && (
          <div
            role="alert"
            className="rise rounded-input border border-coral/50 bg-coral/10 p-4"
          >
            <p className="text-sm text-coral-ink">
              Could not load the graph ({error.code}).
            </p>
            <p className="mt-1 text-xs text-ink-2">{error.message}</p>
            <Button variant="soft" className="btn-sm mt-3" onClick={retry}>
              Retry
            </Button>
          </div>
        )}

        {graph && (
          <>
            {/* Capped and centred: an ego graph does not get more readable by
                being stretched across a 1400px panel. */}
            <div className="mx-auto max-w-3xl rounded-card border border-line bg-paper-2 p-3">
              <EntityGraph
                graph={graph}
                focusedEntityId={state.selectedEntityId}
                onSelectEntity={(id) =>
                  dispatch({ type: "SELECT_ENTITY", entityId: id })
                }
              />
            </div>
            <FocusReadout
              graph={graph}
              focusedEntityId={state.selectedEntityId}
            />
            <Legend graph={graph} />
            <p className="mt-3 text-xs text-ink-3">
              Select any node — by click or with the keyboard — to re-centre the
              picture on it.
            </p>
          </>
        )}
      </div>
    </WorkspaceRegion>
  );
}
