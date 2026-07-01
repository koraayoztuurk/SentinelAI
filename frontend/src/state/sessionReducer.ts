// Session State reducer (pure).
//
// Session State is analyst-scoped and independent of any investigation (Frontend
// Architecture §8, UI State Management §5): preferences such as the theme. The state
// shape and transitions are kept framework-free and independently testable
// (mirroring `workspaceReducer`); the React provider that hosts this reducer and its
// persistence live in `session.tsx`.

export type Theme = "dark" | "light";

export interface SessionState {
  readonly theme: Theme;
}

export type SessionAction =
  | { readonly type: "SET_THEME"; readonly theme: Theme }
  | { readonly type: "TOGGLE_THEME" };

export const defaultSessionState: SessionState = {
  theme: "dark",
};

export function sessionReducer(
  state: SessionState,
  action: SessionAction,
): SessionState {
  switch (action.type) {
    case "SET_THEME":
      return { ...state, theme: action.theme };
    case "TOGGLE_THEME":
      return { ...state, theme: state.theme === "dark" ? "light" : "dark" };
    default: {
      // Exhaustiveness guard: a new action type without a case is a type error.
      const unreachable: never = action;
      return unreachable;
    }
  }
}
