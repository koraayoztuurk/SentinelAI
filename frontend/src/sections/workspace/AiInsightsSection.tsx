// AI Insights region (ES-047).
//
// Replaces the "not yet available" placeholder: presents the Investigation
// Trace — the explainability journal the Investigation Loop writes (ES-045) —
// and hosts the "Run investigation" interaction (ES-044). A run's terminal
// condition is presented explicitly: `completed`, `escalated` (with its
// stable failure code — the ADR-013 degrade-to-escalation made visible to
// the analyst) or `exhausted` (cycle budget). The region never owns data:
// trace entries come from the server-state layer and refresh after each run.

import { useInvestigationTrace } from "../../state/useInvestigationTrace";
import { useRunInvestigation } from "../../state/useRunInvestigation";
import type { RunOutcomeViewModel } from "../../communication/run";
import { Button } from "../../ui/Button";
import { WorkspaceRegion } from "./WorkspaceRegion";

export interface AiInsightsSectionProps {
  readonly investigationId: string;
}

const OUTCOME_STYLES: Record<string, string> = {
  completed: "border-emerald-500/50 text-emerald-400",
  escalated: "border-amber-500/60 text-amber-400",
  exhausted: "border-sky-500/50 text-sky-400",
};

function OutcomeBadge({ outcome }: { readonly outcome: RunOutcomeViewModel }) {
  const style = OUTCOME_STYLES[outcome.end] ?? "border-white/20";
  return (
    <div
      role="status"
      className={`rounded border px-3 py-2 text-sm ${style}`}
      data-testid="run-outcome"
    >
      <span className="font-semibold uppercase">{outcome.end}</span>
      <span className="ml-2 opacity-70">
        after {outcome.cycles} cycle{outcome.cycles === 1 ? "" : "s"}
      </span>
      {outcome.failureCode !== null && (
        <span className="ml-2 font-mono text-xs opacity-80">
          {outcome.failureCode}
        </span>
      )}
    </div>
  );
}

export function AiInsightsSection({ investigationId }: AiInsightsSectionProps) {
  const trace = useInvestigationTrace(investigationId);
  const runState = useRunInvestigation(investigationId);

  return (
    <WorkspaceRegion title="AI Insights">
      <div className="mb-3 flex items-center gap-3">
        <Button
          className="rounded border border-white/20 px-3 py-1 text-sm disabled:opacity-40"
          onClick={runState.run}
          disabled={runState.running}
        >
          {runState.running ? "Running…" : "Run investigation"}
        </Button>
        {runState.outcome && <OutcomeBadge outcome={runState.outcome} />}
      </div>

      {runState.error && (
        <p role="alert" className="mb-3 text-xs text-red-400">
          Run failed ({runState.error.code}): {runState.error.message}
        </p>
      )}

      {trace.error && (
        <p role="alert" className="text-xs text-red-400">
          Could not load the trace ({trace.error.code}).
          <Button className="ml-2 underline" onClick={trace.retry}>
            Retry
          </Button>
        </p>
      )}

      {trace.loading && (
        <p role="status" className="text-sm opacity-50">
          Loading trace…
        </p>
      )}

      {!trace.loading && !trace.error && trace.entries.length === 0 && (
        <p className="text-sm opacity-50">
          No AI activity yet. Run the investigation to let the planner decide.
        </p>
      )}

      {trace.entries.length > 0 && (
        <ol className="grid max-h-72 gap-2 overflow-y-auto text-sm">
          {trace.entries.map((entry) => (
            <li
              key={entry.id}
              className="rounded border border-white/10 px-3 py-2"
            >
              <div className="flex items-center justify-between gap-2">
                <span className="font-mono text-xs uppercase opacity-70">
                  {entry.kind}
                </span>
                <span className="text-xs opacity-50">{entry.actor}</span>
              </div>
              <p className="mt-1">{entry.summary}</p>
            </li>
          ))}
        </ol>
      )}
    </WorkspaceRegion>
  );
}
