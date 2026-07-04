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
  return inMemoryCredential;
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
