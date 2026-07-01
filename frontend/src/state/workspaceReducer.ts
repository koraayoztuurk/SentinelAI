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
  // The entity the graph exploration started from (the chosen seed) and the entity
  // currently focused in the graph. Seed selection sets both; drilling into a graph
  // node moves only the focus, so the origin seed is preserved (ES-026).
  readonly selectedSeedEntityId: string | null;
  readonly selectedEntityId: string | null;
}

export type WorkspaceAction =
  | { readonly type: "SELECT_FINDING"; readonly findingId: string }
  | { readonly type: "SELECT_EVIDENCE"; readonly evidenceId: string }
  | { readonly type: "SELECT_SEED_ENTITY"; readonly entityId: string }
  | { readonly type: "SELECT_ENTITY"; readonly entityId: string }
  | { readonly type: "CLEAR_SELECTION" };

export const initialWorkspaceState: WorkspaceContextState = {
  selectedFindingId: null,
  selectedEvidenceId: null,
  selectedSeedEntityId: null,
  selectedEntityId: null,
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
    case "SELECT_SEED_ENTITY":
      return {
        ...state,
        selectedSeedEntityId: action.entityId,
        selectedEntityId: action.entityId,
      };
    case "SELECT_ENTITY":
      return { ...state, selectedEntityId: action.entityId };
    case "CLEAR_SELECTION":
      return initialWorkspaceState;
    default: {
      // Exhaustiveness guard: a new action type without a case is a type error.
      const unreachable: never = action;
      return unreachable;
    }
  }
}
