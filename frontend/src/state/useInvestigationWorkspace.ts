// Investigation workspace fetch hook.
//
// A minimal local hook that loads the workspace view model and tracks loading and
// error state, mirroring `useInvestigationDashboard` (ES-024). Requests are
// cancelled when the id changes or the component unmounts (Frontend Architecture
// §10 cancellation). A server-state cache / auto-refresh library (TanStack Query) is
// deferred to the State Management specification (ES-027).

import { useEffect, useState } from "react";
import { ApiError } from "../communication/errors";
import {
  loadInvestigationWorkspace,
  type WorkspaceViewModel,
} from "../communication/workspace";

export interface WorkspaceState {
  readonly viewModel: WorkspaceViewModel | null;
  readonly loading: boolean;
  readonly error: ApiError | null;
}

export function useInvestigationWorkspace(id: string): WorkspaceState {
  const [state, setState] = useState<WorkspaceState>({
    viewModel: null,
    loading: true,
    error: null,
  });

  useEffect(() => {
    const controller = new AbortController();
    setState({ viewModel: null, loading: true, error: null });

    loadInvestigationWorkspace(id, controller.signal)
      .then((viewModel) => {
        if (!controller.signal.aborted) {
          setState({ viewModel, loading: false, error: null });
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
        setState({ viewModel: null, loading: false, error });
      });

    return () => controller.abort();
  }, [id]);

  return state;
}
