import { afterEach, describe, expect, it, vi } from "vitest";
import {
  getDevAuthCredential,
  getDevAuthSubject,
  setDevAuthCredential,
} from "./devAuth";

describe("devAuth", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    setDevAuthCredential("");
  });

  it("stores and returns the trimmed credential", () => {
    setDevAuthCredential("  alice:secret-1  ");
    expect(getDevAuthCredential()).toBe("alice:secret-1");
    expect(getDevAuthSubject()).toBe("alice");
  });

  it("clears the credential with a blank value", () => {
    setDevAuthCredential("alice:secret-1");
    setDevAuthCredential("   ");
    expect(getDevAuthCredential()).toBeNull();
    expect(getDevAuthSubject()).toBeNull();
  });

  it("reports no subject for a credential without one", () => {
    setDevAuthCredential(":token-only");
    expect(getDevAuthSubject()).toBeNull();
  });

  it("falls back to the injected dev credential when nothing is stored", () => {
    vi.stubEnv("VITE_DEV_AUTH_CREDENTIAL", "koray:injected-token");
    setDevAuthCredential("");
    expect(getDevAuthCredential()).toBe("koray:injected-token");
    expect(getDevAuthSubject()).toBe("koray");
  });

  it("prefers an explicitly entered credential over the injected one", () => {
    vi.stubEnv("VITE_DEV_AUTH_CREDENTIAL", "koray:injected-token");
    setDevAuthCredential("alice:typed-token");
    expect(getDevAuthCredential()).toBe("alice:typed-token");
    expect(getDevAuthSubject()).toBe("alice");
  });
});
