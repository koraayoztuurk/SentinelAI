// Development authentication credential (Session State, ES-047).
//
// The backend's development-grade authenticator (ES-046) expects
// `Authorization: Bearer <subject>:<token>`. The analyst enters that
// credential once (header field); it persists in localStorage like the other
// session preferences and feeds the api client's pluggable token source —
// the first real use of the ES-023 seam. The production identity flow
// replaces this in a later phase.

const STORAGE_KEY = "sentinelai.devAuth";

// Web Storage is not fully implemented on every runtime (the test runtime
// included, see test/setup.ts), so the store keeps an in-memory mirror and
// treats localStorage as best-effort persistence.
let inMemoryCredential: string | null = null;

// Development convenience (ES-054): `VITE_DEV_AUTH_CREDENTIAL` in
// `frontend/.env.local` (gitignored) signs the sole developer in without
// typing. Dev-server builds only — production builds never carry the
// variable, so the deployed flow is unchanged. An explicitly entered
// credential always wins over the injected one.
function injectedDevCredential(): string | null {
  if (!import.meta.env.DEV) {
    return null;
  }
  const value = import.meta.env.VITE_DEV_AUTH_CREDENTIAL;
  if (typeof value === "string" && value.trim().length > 0) {
    return value.trim();
  }
  return null;
}

/** The stored credential (`subject:token`), or null when not configured. */
export function getDevAuthCredential(): string | null {
  try {
    const value = localStorage.getItem(STORAGE_KEY);
    if (value && value.trim().length > 0) {
      return value.trim();
    }
  } catch {
    /* fall through to the in-memory mirror */
  }
  return inMemoryCredential ?? injectedDevCredential();
}

/** Persist (or clear, with a blank value) the credential. */
export function setDevAuthCredential(value: string): void {
  const trimmed = value.trim();
  inMemoryCredential = trimmed.length === 0 ? null : trimmed;
  try {
    if (trimmed.length === 0) {
      localStorage.removeItem(STORAGE_KEY);
    } else {
      localStorage.setItem(STORAGE_KEY, trimmed);
    }
  } catch {
    /* Storage may be unavailable; the in-memory mirror still serves the session. */
  }
}

/** The subject part of the credential (the analyst identity), or null. */
export function getDevAuthSubject(): string | null {
  const credential = getDevAuthCredential();
  if (credential === null) {
    return null;
  }
  const subject = credential.split(":", 1)[0] ?? "";
  return subject.trim().length > 0 ? subject.trim() : null;
}
