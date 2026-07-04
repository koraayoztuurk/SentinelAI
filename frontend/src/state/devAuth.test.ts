import { describe, expect, it } from "vitest";
import {
  getDevAuthCredential,
  getDevAuthSubject,
  setDevAuthCredential,
} from "./devAuth";

describe("devAuth", () => {
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
});
