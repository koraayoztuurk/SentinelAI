// Investigation Context (minimal, presentation-only).
//
// The shared operational state of the Investigation Workspace
// (investigation-workspace §6). Workspace regions do not talk to each other
// directly (interaction-model §6); they consume this context and emit only the
// selection they own (ui-state-management §6). It holds the current selections and
// nothing else — highlights are derived, not stored.
//
// This is deliberately plain React (context + reducer): the server-state cache
// (TanStack Query) and the promoted global store belong to State Management
// (ES-027). The pure state/reducer lives in `workspaceReducer.ts`.

import {
  createContext,
  useContext,
  useMemo,
  useReducer,
  type Dispatch,
  type ReactNode,
} from "react";
import {
  initialWorkspaceState,
  workspaceReducer,
  type WorkspaceAction,
  type WorkspaceContextState,
} from "./workspaceReducer";

interface WorkspaceContextValue {
  readonly state: WorkspaceContextState;
  readonly dispatch: Dispatch<WorkspaceAction>;
}

const WorkspaceContext = createContext<WorkspaceContextValue | null>(null);

export function WorkspaceProvider({ children }: { readonly children: ReactNode }) {
  const [state, dispatch] = useReducer(workspaceReducer, initialWorkspaceState);
  const value = useMemo(() => ({ state, dispatch }), [state]);
  return (
    <WorkspaceContext.Provider value={value}>
      {children}
    </WorkspaceContext.Provider>
  );
}

// The context hook is intentionally co-located with its provider (the idiomatic
// React pattern); it is not a fast-refresh component export.
// eslint-disable-next-line react-refresh/only-export-components
export function useWorkspaceContext(): WorkspaceContextValue {
  const value = useContext(WorkspaceContext);
  if (value === null) {
    throw new Error("useWorkspaceContext must be used within a WorkspaceProvider.");
  }
  return value;
}
