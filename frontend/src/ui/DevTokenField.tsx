// Development credential field (ES-047).
//
// The analyst enters the development bearer credential
// (`subject:token`, ES-046) once; it persists as Session State and feeds the
// api client's token source. Presentation only — the value is applied on
// commit (Enter/blur) and never displayed back in full.
//
// Signed-in state is carried by a mint dot plus the subject's name, so identity
// is legible at a glance without the field shouting for attention.

import { useState } from "react";
import {
  getDevAuthCredential,
  getDevAuthSubject,
  setDevAuthCredential,
} from "../state/devAuth";

export function DevTokenField() {
  const [draft, setDraft] = useState("");
  const [subject, setSubject] = useState(getDevAuthSubject());

  const commit = () => {
    if (draft.trim().length === 0 && getDevAuthCredential() === null) {
      return;
    }
    setDevAuthCredential(draft);
    setSubject(getDevAuthSubject());
    setDraft("");
  };

  const signedIn = subject !== null;

  return (
    <label className="flex min-w-0 items-center gap-2">
      <span
        className={`chip min-w-0 cursor-default ${
          signedIn ? "text-mint-ink" : "text-ink-3"
        }`}
      >
        <span
          aria-hidden="true"
          className={`tag-dot ${signedIn ? "" : "opacity-40"}`}
        />
        <span className="min-w-0 truncate">
          {signedIn ? `Signed in: ${subject}` : "Dev token"}
        </span>
      </span>
      <input
        type="password"
        value={draft}
        placeholder={signedIn ? "change…" : "subject:token"}
        aria-label="Development credential"
        className={`input mono-label px-2.5 py-1.5 ${
          signedIn ? "w-16 sm:w-24" : "w-28 sm:w-36"
        }`}
        onChange={(event) => setDraft(event.target.value)}
        onBlur={commit}
        onKeyDown={(event) => {
          if (event.key === "Enter") {
            commit();
          }
        }}
      />
    </label>
  );
}
