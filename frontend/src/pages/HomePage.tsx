// Landing page (ES-047).
//
// Entry point of the live flow: the analyst creates an investigation here and
// is taken to its workspace. The owner is derived server-side from the
// authenticated subject (ES-062 owner==subject: the creator owns what they
// create) — the form no longer supplies it, but a credential is still required
// to create. The platform-level investigation list remains deferred.

import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useCreateInvestigation } from "../state/useCreateInvestigation";
import { getDevAuthSubject } from "../state/devAuth";
import { Button } from "../ui/Button";

export function HomePage() {
  const navigate = useNavigate();
  const [title, setTitle] = useState("");
  const [priority, setPriority] = useState("high");
  const subject = getDevAuthSubject();
  const { create, creating, error } = useCreateInvestigation((investigation) =>
    navigate(`/investigations/${investigation.id}/workspace`),
  );

  const submit = () => {
    if (title.trim().length === 0 || subject === null) {
      return;
    }
    create({ title: title.trim(), priority });
  };

  return (
    <section className="mx-auto max-w-xl">
      <h1 className="text-xl font-semibold">SentinelAI</h1>
      <p className="mt-2 text-sm opacity-80">
        AI-assisted cybersecurity investigations.
      </p>

      <div className="mt-6 grid gap-3 rounded-lg border border-white/10 p-5">
        <h2 className="text-sm font-semibold">New investigation</h2>
        {subject === null && (
          <p className="text-xs opacity-60">
            Enter your development credential (top right) to start an
            investigation.
          </p>
        )}
        <input
          aria-label="Investigation title"
          placeholder="What are you investigating?"
          value={title}
          className="rounded border border-white/20 bg-transparent px-3 py-2 text-sm"
          onChange={(event) => setTitle(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              submit();
            }
          }}
        />
        <div className="flex items-center gap-3">
          <select
            aria-label="Priority"
            value={priority}
            className="rounded border border-white/20 bg-transparent px-2 py-2 text-sm"
            onChange={(event) => setPriority(event.target.value)}
          >
            <option value="high">high</option>
            <option value="medium">medium</option>
            <option value="low">low</option>
          </select>
          <Button
            className="rounded border border-white/20 px-4 py-2 text-sm disabled:opacity-40"
            onClick={submit}
            disabled={creating || subject === null}
          >
            {creating ? "Creating…" : "Create investigation"}
          </Button>
        </div>
        {error && (
          <p role="alert" className="text-xs text-red-400">
            Could not create the investigation ({error.code}): {error.message}
          </p>
        )}
      </div>
    </section>
  );
}
