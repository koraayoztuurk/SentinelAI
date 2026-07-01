// Session State store (app-level).
//
// The single owner of analyst preferences (Session State, Frontend Architecture §8 /
// UI State Management §6). It is mounted at the application root because Session
// State is analyst-scoped and independent of any investigation. It currently owns the
// theme; new preferences extend the same store. The pure state/reducer lives in
// `sessionReducer.ts`; persistence (localStorage) and DOM application live here.

import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useReducer,
  type ReactNode,
} from "react";
import {
  defaultSessionState,
  sessionReducer,
  type SessionState,
  type Theme,
} from "./sessionReducer";

const THEME_STORAGE_KEY = "sentinelai.theme";

function readStoredTheme(): Theme {
  try {
    const stored = localStorage.getItem(THEME_STORAGE_KEY);
    if (stored === "dark" || stored === "light") {
      return stored;
    }
  } catch {
    // localStorage may be unavailable (private mode); fall back to the default.
  }
  return defaultSessionState.theme;
}

interface SessionContextValue {
  readonly theme: Theme;
  readonly setTheme: (theme: Theme) => void;
  readonly toggleTheme: () => void;
}

const SessionContext = createContext<SessionContextValue | null>(null);

export function SessionProvider({ children }: { readonly children: ReactNode }) {
  const [state, dispatch] = useReducer(
    sessionReducer,
    undefined,
    (): SessionState => ({ theme: readStoredTheme() }),
  );

  useEffect(() => {
    document.documentElement.dataset.theme = state.theme;
    try {
      localStorage.setItem(THEME_STORAGE_KEY, state.theme);
    } catch {
      // Persistence is best-effort; the theme still applies for the session.
    }
  }, [state.theme]);

  const value = useMemo<SessionContextValue>(
    () => ({
      theme: state.theme,
      setTheme: (theme) => dispatch({ type: "SET_THEME", theme }),
      toggleTheme: () => dispatch({ type: "TOGGLE_THEME" }),
    }),
    [state.theme],
  );

  return (
    <SessionContext.Provider value={value}>{children}</SessionContext.Provider>
  );
}

// The context hook is intentionally co-located with its provider (the idiomatic
// React pattern); it is not a fast-refresh component export.
// eslint-disable-next-line react-refresh/only-export-components
export function useSession(): SessionContextValue {
  const value = useContext(SessionContext);
  if (value === null) {
    throw new Error("useSession must be used within a SessionProvider.");
  }
  return value;
}
