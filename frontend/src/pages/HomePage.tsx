// Landing page (ES-047).
//
// Entry point of the live flow: the analyst creates an investigation here and
// is taken to its workspace. The owner is derived server-side from the
// authenticated subject (ES-062 owner==subject: the creator owns what they
// create) — the form no longer supplies it, but a credential is still required
// to create. The platform-level investigation list remains deferred.
//
// The page carries one job beyond the form: telling a first-time reader what
// the product does. The right-hand rail spells the run out in four steps,
// because "the agents correlate it" means nothing until you can see the order
// things happen in.

import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useCreateInvestigation } from "../state/useCreateInvestigation";
import { getDevAuthSubject } from "../state/devAuth";
import {
  forgetInvestigation,
  listRecentInvestigations,
  type RecentInvestigation,
} from "../state/recentInvestigations";
import { Button } from "../ui/Button";

interface Step {
  readonly n: string;
  readonly title: string;
  readonly body: string;
  readonly tone: string;
}

const RUN_STEPS: readonly Step[] = [
  {
    n: "01",
    title: "It gathers context",
    body: "Related past investigations, the entities standing next to yours in the knowledge graph, and matching ATT&CK techniques or CVEs.",
    tone: "text-cyan-ink",
  },
  {
    n: "02",
    title: "A planner decides the next move",
    body: "One step at a time — re-read the case, pull a memory item, walk the graph — until it has enough or decides it cannot get further.",
    tone: "text-lav-ink",
  },
  {
    n: "03",
    title: "The findings get checked",
    body: "A separate agent tests each finding against the evidence behind it and reports what does not hold up.",
    tone: "text-mint-ink",
  },
  {
    n: "04",
    title: "You get one recommendation",
    body: "With its confidence, the conflicts it noticed and the questions it could not answer. What to do about it stays your call.",
    tone: "text-pear-ink",
  },
];

function RunRail() {
  return (
    <aside className="surface surface-quiet p-5 sm:p-6">
      <h2 className="text-base font-bold tracking-tight">
        What happens when you press <span className="hl">Run</span>
      </h2>
      <ol className="mt-5 grid gap-5">
        {RUN_STEPS.map((step) => (
          <li key={step.n} className="grid grid-cols-[2.25rem_minmax(0,1fr)] gap-3">
            <span
              className={`mono-label pt-0.5 font-semibold tabular-nums ${step.tone}`}
              aria-hidden="true"
            >
              {step.n}
            </span>
            <div className="min-w-0">
              <p className="text-sm font-semibold">{step.title}</p>
              <p className="mt-1 text-[0.8125rem] leading-relaxed text-ink-2">
                {step.body}
              </p>
            </div>
          </li>
        ))}
      </ol>
      <p className="mt-5 border-t border-line pt-4 text-xs leading-relaxed text-ink-3">
        If the AI provider is unreachable the run stops safely and says so. It
        never leaves an investigation half-written.
      </p>
    </aside>
  );
}

/**
 * Getting back into a case.
 *
 * The platform exposes no investigation-list endpoint, so this cannot be "all
 * your investigations" and does not pretend to be: it is what this browser has
 * opened, plus a field for an identifier that arrived from somewhere else (a
 * ticket, a colleague, a page you had open yesterday).
 */
function ContinueInvestigation() {
  const navigate = useNavigate();
  const [recent, setRecent] = useState<readonly RecentInvestigation[]>(() =>
    listRecentInvestigations(),
  );
  const [lookupId, setLookupId] = useState("");

  const open = () => {
    const id = lookupId.trim();
    if (id.length === 0) {
      return;
    }
    navigate(`/investigations/${encodeURIComponent(id)}/workspace`);
  };

  const forget = (id: string) => {
    forgetInvestigation(id);
    setRecent(listRecentInvestigations());
  };

  return (
    <section className="surface surface-quiet mt-5 max-w-xl p-5 sm:p-6">
      <h2 className="text-base font-bold tracking-tight">
        Continue an investigation
      </h2>
      <p className="region-note">
        Cases you opened in this browser. The platform has no server-side list
        yet, so this is per-device — paste an identifier to reach any other one.
      </p>

      {recent.length > 0 && (
        <ul className="mt-4 grid gap-2">
          {recent.map((entry) => (
            <li key={entry.id} className="flex items-center gap-2">
              <Link
                to={`/investigations/${entry.id}/workspace`}
                className="card min-w-0 flex-1 px-3.5 py-2.5 no-underline"
              >
                <span className="block truncate text-sm font-semibold text-ink">
                  {entry.title || entry.id}
                </span>
                <span className="mono-label mt-0.5 block truncate text-ink-3">
                  {entry.id}
                </span>
              </Link>
              <Button
                variant="outline"
                className="btn-sm shrink-0"
                onClick={() => forget(entry.id)}
                title={`Remove ${entry.title || entry.id} from this list`}
              >
                Forget
              </Button>
            </li>
          ))}
        </ul>
      )}

      <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-line pt-4">
        <input
          aria-label="Investigation identifier"
          placeholder="Open by identifier…"
          value={lookupId}
          className="input min-w-40 flex-1"
          onChange={(event) => setLookupId(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              open();
            }
          }}
        />
        <Button
          variant="soft"
          onClick={open}
          disabled={lookupId.trim().length === 0}
        >
          Open
        </Button>
      </div>
    </section>
  );
}

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
    <div className="rise-seq grid items-start gap-8 lg:grid-cols-[minmax(0,1.15fr)_minmax(0,0.85fr)] lg:gap-12">
      <div className="min-w-0">
        <p className="eyebrow">AI-assisted cyber investigations</p>
        <h1 className="mt-3 text-[clamp(2.5rem,6vw,3.75rem)] font-bold leading-[1.02]">
          SentinelAI
        </h1>
        <p className="mt-4 max-w-xl text-lg leading-relaxed text-ink-2">
          Open a case, attach what you found, and let the agents correlate it
          against your organisation&rsquo;s memory, its knowledge graph and public
          threat intelligence.{" "}
          <span className="hl">Every step they take is written down</span> — so
          you can check the reasoning instead of trusting it.
        </p>

        <section className="surface mt-8 max-w-xl p-5 sm:p-6">
          <h2 className="text-base font-bold tracking-tight">
            Start an investigation
          </h2>
          <p className="region-note">
            Give it a name you would still recognise in a week. Evidence,
            findings and the agent run all live inside it once it is open.
          </p>

          {subject === null && (
            <p className="mt-4 flex items-start gap-2 rounded-input border border-amber/50 bg-amber/10 px-3 py-2.5 text-[0.8125rem] leading-relaxed text-amber-ink">
              <span className="tag-dot mt-1.5" aria-hidden="true" />
              <span>
                Enter your development credential in the top-right corner first —
                an investigation belongs to whoever created it.
              </span>
            </p>
          )}

          <div className="mt-4 grid gap-3">
            <input
              aria-label="Investigation title"
              placeholder="e.g. Repeated failed logins on the finance subnet"
              value={title}
              className="input"
              onChange={(event) => setTitle(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter") {
                  submit();
                }
              }}
            />
            <div className="flex flex-wrap items-center gap-3">
              <label className="flex items-center gap-2 text-[0.8125rem] text-ink-2">
                Priority
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
              </label>
              <Button
                variant="primary"
                className="ml-auto"
                onClick={submit}
                busy={creating}
                disabled={subject === null}
              >
                {creating ? "Creating…" : "Create investigation"}
              </Button>
            </div>
          </div>

          {error && (
            <p
              role="alert"
              className="mt-3 rounded-input border border-coral/50 bg-coral/10 px-3 py-2 text-[0.8125rem] text-coral-ink"
            >
              Could not create the investigation ({error.code}): {error.message}
            </p>
          )}
        </section>

        <ContinueInvestigation />
      </div>

      <RunRail />
    </div>
  );
}
