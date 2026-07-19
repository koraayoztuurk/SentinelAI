// AI Insights region (ES-047, outcome panel ES-055).
//
// Replaces the "not yet available" placeholder: presents the Investigation
// Trace — the explainability journal the Investigation Loop writes (ES-045) —
// hosts the "Run investigation" interaction (ES-044) and presents the
// synthesized Investigation Outcome (the Decision Engine's recommendation,
// confidence, conflicts and open questions — advisory only, the analyst
// decides). A run's terminal condition is presented explicitly: `completed`,
// `escalated` (with its stable failure code — the ADR-013
// degrade-to-escalation made visible to the analyst) or `exhausted` (cycle
// budget). The region never owns data: trace entries and the outcome come
// from the server-state layer and refresh after each run.

import { useInvestigationOutcome } from "../../state/useInvestigationOutcome";
import { useInvestigationTrace } from "../../state/useInvestigationTrace";
import { useRunInvestigation } from "../../state/useRunInvestigation";
import type { OutcomeViewModel } from "../../communication/outcome";
import type { RunOutcomeViewModel } from "../../communication/run";
import { Button } from "../../ui/Button";
import { WorkspaceRegion } from "./WorkspaceRegion";

export interface AiInsightsSectionProps {
  readonly investigationId: string;
}

const OUTCOME_STYLES: Record<string, string> = {
  completed: "border-ok/50 text-ok",
  escalated: "border-warn/60 text-warn",
  exhausted: "border-info/50 text-info",
};

function OutcomeBadge({ outcome }: { readonly outcome: RunOutcomeViewModel }) {
  const style = OUTCOME_STYLES[outcome.end] ?? "border-line-strong";
  return (
    <div
      role="status"
      className={`fade-up rounded-md border bg-panel-2/60 px-3 py-2 text-sm ${style}`}
      data-testid="run-outcome"
    >
      <span className="font-semibold uppercase">{outcome.end}</span>
      <span className="ml-2 text-muted">
        after {outcome.cycles} cycle{outcome.cycles === 1 ? "" : "s"}
      </span>
      {outcome.failureCode !== null && (
        <span className="mono-label ml-2">{outcome.failureCode}</span>
      )}
    </div>
  );
}

function SynthesizedOutcomePanel({
  outcome,
}: {
  readonly outcome: OutcomeViewModel;
}) {
  return (
    <div
      data-testid="synthesized-outcome"
      className="fade-up mb-3 rounded-md border border-ai/40 bg-ai/5 px-3 py-2 text-sm"
    >
      <div className="flex items-center justify-between gap-2">
        <span className="mono-label uppercase text-ai">
          Synthesized outcome
        </span>
        <span className="mono-label tabular-nums text-muted">
          confidence {Math.round(outcome.confidence * 100)}%
        </span>
      </div>
      <p className="mt-1">{outcome.recommendation}</p>
      {outcome.detectedConflicts.length > 0 && (
        <p className="mt-1 text-xs text-warn">
          Conflicts: {outcome.detectedConflicts.join("; ")}
        </p>
      )}
      {outcome.openQuestions.length > 0 && (
        <p className="mt-1 text-xs text-muted">
          Open questions: {outcome.openQuestions.join("; ")}
        </p>
      )}
    </div>
  );
}

export function AiInsightsSection({ investigationId }: AiInsightsSectionProps) {
  const trace = useInvestigationTrace(investigationId);
  const runState = useRunInvestigation(investigationId);
  const synthesized = useInvestigationOutcome(investigationId);

  return (
    <WorkspaceRegion title="AI Insights">
      <div className="mb-3 flex items-center gap-3">
        <Button
          className="btn btn-primary"
          onClick={runState.run}
          disabled={runState.running}
        >
          {runState.running ? "Running…" : "Run investigation"}
        </Button>
        {runState.running && (
          <span className="status-dot [--pulse:var(--color-ai)]" aria-hidden="true" />
        )}
        {runState.outcome && <OutcomeBadge outcome={runState.outcome} />}
      </div>

      {synthesized.outcome && (
        <SynthesizedOutcomePanel outcome={synthesized.outcome} />
      )}

      {runState.error && (
        <p role="alert" className="mb-3 text-xs text-danger">
          Run failed ({runState.error.code}): {runState.error.message}
        </p>
      )}

      {trace.error && (
        <p role="alert" className="text-xs text-danger">
          Could not load the trace ({trace.error.code}).
          <Button className="btn-link ml-2 text-xs" onClick={trace.retry}>
            Retry
          </Button>
        </p>
      )}

      {trace.loading && (
        <div role="status" className="grid gap-2">
          <span className="sr-only">Loading trace…</span>
          <div className="shimmer h-10 w-full" aria-hidden="true" />
          <div className="shimmer h-10 w-4/5" aria-hidden="true" />
        </div>
      )}

      {!trace.loading && !trace.error && trace.entries.length === 0 && (
        <p className="text-sm text-faint">
          No AI activity yet. Run the investigation to let the planner decide.
        </p>
      )}

      {trace.entries.length > 0 && (
        <ol className="stagger grid max-h-72 gap-2 overflow-y-auto text-sm">
          {trace.entries.map((entry) => (
            <li key={entry.id} className="card border-l-2 border-l-ai/60 px-3 py-2">
              <div className="flex items-center justify-between gap-2">
                <span className="mono-label uppercase text-ai">
                  {entry.kind}
                </span>
                <span className="mono-label text-faint">{entry.actor}</span>
              </div>
              <p className="mt-1">{entry.summary}</p>
            </li>
          ))}
        </ol>
      )}
    </WorkspaceRegion>
  );
}
