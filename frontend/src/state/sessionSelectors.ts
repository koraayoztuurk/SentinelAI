// Session State selectors (pure, Derived State reads).
//
// Read-only derivations over the Session State, mirroring the workspace selectors.
// Establishing the selector pattern for Session State now means future preferences
// are read the same way rather than reaching into the state shape directly.

import type { SessionState, Theme } from "./sessionReducer";

export function selectTheme(state: SessionState): Theme {
  return state.theme;
}

export function selectIsDark(state: SessionState): boolean {
  return state.theme === "dark";
}

export function selectIsLight(state: SessionState): boolean {
  return state.theme === "light";
}
