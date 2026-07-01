// Entity neighbourhood fetch hook.
//
// Loads the ego graph for the currently focused entity, mirroring
// `useInvestigationWorkspace` (ES-025). When no entity is focused (`entityId` is
// null) the hook stays idle. Requests are cancelled when the focused entity changes
// or the component unmounts (Frontend Architecture §10 cancellation). The
// server-state cache library (TanStack Query) is deferred to ES-027.

import { useEffect, useState } from "react";
import { ApiError } from "../communication/errors";
import {
  loadEntityNeighborhood,
  type GraphViewModel,
} from "../communication/graph";

export interface NeighborhoodState {
  readonly graph: GraphViewModel | null;
  readonly loading: boolean;
  readonly error: ApiError | null;
}

const IDLE: NeighborhoodState = { graph: null, loading: false, error: null };

export function useEntityNeighborhood(
  entityId: string | null,
  reloadToken = 0,
): NeighborhoodState {
  const [state, setState] = useState<NeighborhoodState>(IDLE);

  useEffect(() => {
    if (entityId === null) {
      setState(IDLE);
      return;
    }

    const controller = new AbortController();
    setState({ graph: null, loading: true, error: null });

    loadEntityNeighborhood(entityId, controller.signal)
      .then((graph) => {
        if (!controller.signal.aborted) {
          setState({ graph, loading: false, error: null });
        }
      })
      .catch((cause: unknown) => {
        if (controller.signal.aborted) {
          return;
        }
        const error =
          cause instanceof ApiError
            ? cause
            : new ApiError("communication.error", "The request failed.", 0);
        setState({ graph: null, loading: false, error });
      });

    return () => controller.abort();
  }, [entityId, reloadToken]);

  return state;
}
