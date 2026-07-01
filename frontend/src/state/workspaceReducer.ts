// Investigation Context reducer (pure).
//
// The state shape and transitions of the shared Investigation Context
// (investigation-workspace §6), kept framework-free and independently testable. The
// reducer uses discriminated-union actions with an exhaustive switch, so every
// action is handled and a new action type without a case is a compile-time error.
// The React provider/hook that host this reducer live in `workspaceContext.tsx`.

export interface WorkspaceContextState {
  readonly selectedFindingId: string | null;
  readonly selectedEvidenceId: string | null;
}

export type WorkspaceAction =
  | { readonly type: "SELECT_FINDING"; readonly findingId: string }
  | { readonly type: "SELECT_EVIDENCE"; readonly evidenceId: string }
  | { readonly type: "CLEAR_SELECTION" };

export const initialWorkspaceState: WorkspaceContextState = {
  selectedFindingId: null,
  selectedEvidenceId: null,
};

export function workspaceReducer(
  state: WorkspaceContextState,
  action: WorkspaceAction,
): WorkspaceContextState {
  switch (action.type) {
    case "SELECT_FINDING":
      return { ...state, selectedFindingId: action.findingId };
    case "SELECT_EVIDENCE":
      return { ...state, selectedEvidenceId: action.evidenceId };
    case "CLEAR_SELECTION":
      return initialWorkspaceState;
    default: {
      // Exhaustiveness guard: a new action type without a case is a type error.
      const unreachable: never = action;
      return unreachable;
    }
  }
}
