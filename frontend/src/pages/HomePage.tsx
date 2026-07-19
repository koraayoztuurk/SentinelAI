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
    <section className="stagger mx-auto max-w-xl pt-10 sm:pt-16">
      <p className="mono-label uppercase text-accent">
        // AI-assisted cyber investigations
      </p>
      <h1
        aria-label="SentinelAI"
        className="mt-3 text-4xl font-bold tracking-tight sm:text-5xl"
      >
        Sentinel
        <span className="text-accent drop-shadow-[0_0_18px_var(--color-accent)]">
          AI
        </span>
      </h1>
      <p className="mt-3 max-w-md text-sm leading-relaxed text-muted">
        Open an investigation, attach evidence, and let the agent runtime
        correlate, reason and explain — every step lands in the trace.
      </p>

      <div className="panel mt-8 grid gap-3 p-5">
        <h2 className="panel-title">New investigation</h2>
        {subject === null && (
          <p className="mono-label text-warn">
            Enter your development credential (top right) to start an
            investigation.
          </p>
        )}
        <input
          aria-label="Investigation title"
          placeholder="What are you investigating?"
          value={title}
          className="input"
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
            className="input py-2"
            onChange={(event) => setPriority(event.target.value)}
          >
            <option value="high">high</option>
            <option value="medium">medium</option>
            <option value="low">low</option>
          </select>
          <Button
            className="btn btn-primary"
            onClick={submit}
            disabled={creating || subject === null}
          >
            {creating ? "Creating…" : "Create investigation"}
          </Button>
        </div>
        {error && (
          <p role="alert" className="text-xs text-danger">
            Could not create the investigation ({error.code}): {error.message}
          </p>
        )}
      </div>
    </section>
  );
}
