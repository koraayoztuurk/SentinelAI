// Recently opened investigations (Session State).
//
// The platform has no investigation-list endpoint: `/api/v1/investigations`
// accepts POST only, so there is no server-side answer to "which cases exist".
// Until one exists, the analyst still needs a way back into a case they opened
// five minutes ago — otherwise the identifier in the address bar is the only
// route, which is not a usable product.
//
// This is a **client-side convenience, not a substitute for the missing
// endpoint**, and it behaves like one:
//
// - it holds only what this browser has actually opened, so it is per-device and
//   never claims to be the full list;
// - it stores the id and the title the page already displayed — no extra
//   requests, no data the analyst has not already been shown;
// - a remembered case can have been erased or handed to someone else since, so
//   opening one is an ordinary authorized request that can legitimately 404 or
//   403. The list is a shortcut, never a permission.
//
// It is Session State in the ui-state-management sense — analyst-scoped,
// independent of any one investigation, persisted in localStorage — and follows
// the `devAuth` store's shape, including the in-memory mirror for runtimes where
// Web Storage is unavailable.

const STORAGE_KEY = "sentinelai.recentInvestigations";
const LIMIT = 8;

export interface RecentInvestigation {
  readonly id: string;
  readonly title: string;
  /** ISO timestamp of the most recent visit, for ordering and display. */
  readonly openedAt: string;
}

let inMemory: readonly RecentInvestigation[] = [];

function isRecent(value: unknown): value is RecentInvestigation {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const candidate = value as Record<string, unknown>;
  return (
    typeof candidate.id === "string" &&
    candidate.id.trim().length > 0 &&
    typeof candidate.title === "string" &&
    typeof candidate.openedAt === "string"
  );
}

function read(): readonly RecentInvestigation[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw !== null) {
      const parsed: unknown = JSON.parse(raw);
      if (Array.isArray(parsed)) {
        // Anything that does not match the shape is dropped rather than
        // trusted: the store is written by older builds too.
        return parsed.filter(isRecent).slice(0, LIMIT);
      }
    }
  } catch {
    /* unavailable or corrupt storage falls back to the in-memory mirror */
  }
  return inMemory;
}

function write(entries: readonly RecentInvestigation[]): void {
  inMemory = entries;
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(entries));
  } catch {
    /* Storage may be unavailable; the mirror still serves this session. */
  }
}

/** The remembered investigations, most recently opened first. */
export function listRecentInvestigations(): readonly RecentInvestigation[] {
  return read();
}

/**
 * Record a visit. Re-opening a case moves it to the front and refreshes its
 * title, so a renamed investigation does not keep its stale label.
 * `openedAt` is caller-supplied, mirroring the platform's discipline of never
 * reading a clock inside a store.
 */
export function rememberInvestigation(
  id: string,
  title: string,
  openedAt: string,
): void {
  const trimmedId = id.trim();
  if (trimmedId.length === 0) {
    return;
  }
  const rest = read().filter((entry) => entry.id !== trimmedId);
  write([{ id: trimmedId, title: title.trim(), openedAt }, ...rest].slice(0, LIMIT));
}

/** Drop one investigation from the list (it was erased, or is simply noise). */
export function forgetInvestigation(id: string): void {
  write(read().filter((entry) => entry.id !== id.trim()));
}
