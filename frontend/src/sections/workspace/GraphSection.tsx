// Graph region (visualization-architecture §5, investigation-workspace §5).
//
// The Graph Visualization region of the Investigation Workspace. It is entity-seeded
// (the backend Graph API has no investigation→graph endpoint): the seeds are the
// entities referenced by the confirmed findings. Selecting a seed starts the
// exploration (and highlights the active seed); the focused entity's neighbourhood
// is loaded and drawn as an SVG ego-graph. Clicking a node drills down by moving the
// focus, preserving the origin seed. All coordination flows through the shared
// Investigation Context — regions never talk to each other directly.

import { Button } from "../../ui/Button";
import { useWorkspaceContext } from "../../state/workspaceContext";
import { useEntityNeighborhood } from "../../state/useEntityNeighborhood";
import { EntitySeedChip } from "../../components/workspace/EntitySeedChip";
import { EntityGraph } from "../../components/workspace/EntityGraph";
import { WorkspaceRegion } from "./WorkspaceRegion";

export interface GraphSectionProps {
  readonly seedEntities: readonly string[];
}

export function GraphSection({ seedEntities }: GraphSectionProps) {
  const { state, dispatch } = useWorkspaceContext();
  const { graph, loading, error, retry } = useEntityNeighborhood(
    state.selectedEntityId,
  );

  if (seedEntities.length === 0) {
    return (
      <WorkspaceRegion title="Graph">
        <p className="text-sm opacity-50">No entities to explore yet.</p>
      </WorkspaceRegion>
    );
  }

  return (
    <WorkspaceRegion title="Graph">
      <div className="flex flex-wrap gap-2">
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
      </div>

      <div className="mt-4">
        {state.selectedEntityId === null && (
          <p className="text-sm opacity-50">
            Select an entity to explore its neighbourhood.
          </p>
        )}

        {loading && (
          <p role="status" className="text-sm opacity-60">
            Loading graph…
          </p>
        )}

        {error && (
          <div role="alert" className="rounded-lg border border-red-500/40 p-4">
            <p className="text-sm">Could not load the graph ({error.code}).</p>
            <p className="mt-1 text-xs opacity-60">{error.message}</p>
            <Button
              className="mt-3 rounded border border-white/20 px-3 py-1 text-sm"
              onClick={retry}
            >
              Retry
            </Button>
          </div>
        )}

        {graph && (
          <EntityGraph
            graph={graph}
            focusedEntityId={state.selectedEntityId}
            onSelectEntity={(id) =>
              dispatch({ type: "SELECT_ENTITY", entityId: id })
            }
          />
        )}
      </div>
    </WorkspaceRegion>
  );
}
