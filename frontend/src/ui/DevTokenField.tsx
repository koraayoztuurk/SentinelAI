// Development credential field (ES-047).
//
// The analyst enters the development bearer credential
// (`subject:token`, ES-046) once; it persists as Session State and feeds the
// api client's token source. Presentation only — the value is applied on
// commit (Enter/blur) and never displayed back in full.

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

  return (
    <label className="flex items-center gap-2 text-xs opacity-80">
      <span>
        {subject === null ? "Dev token" : `Signed in: ${subject}`}
      </span>
      <input
        type="password"
        value={draft}
        placeholder="subject:token"
        aria-label="Development credential"
        className="w-40 rounded border border-white/20 bg-transparent px-2 py-1"
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
