// AI Insights region (ES-047, outcome panel ES-055).
//
// Presents the Investigation Trace — the explainability journal the
// Investigation Loop writes (ES-045) — hosts the "Run investigation"
// interaction (ES-044) and presents the synthesized Investigation Outcome (the
// Decision Engine's recommendation, confidence, conflicts and open questions —
// advisory only, the analyst decides). A run's terminal condition is presented
// explicitly: `completed`, `escalated` (with its stable failure code — the
// ADR-013 degrade-to-escalation made visible to the analyst) or `exhausted`
// (cycle budget). The region never owns data: trace entries and the outcome
// come from the server-state layer and refresh after each run.
//
// One presentation decision carries the region: the trace's vocabulary is
// machine-shaped (`planner_decision`, `outcome_synthesis`) and means nothing to
// someone meeting it for the first time. Each entry is therefore titled in
// plain language, with the raw kind kept beside it — the journal stays
// verifiable without requiring the reader to already know the platform.

import { useEffect, useState } from "react";
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

interface StepStyle {
  readonly title: string;
  readonly tone: string;
}

// The trace vocabulary (domain/trace.py TraceEntryKind), said out loud.
const STEP: Record<string, StepStyle> = {
  retrieval: { title: "Gathered context", tone: "text-cyan-ink" },
  graph_analysis: { title: "Read the knowledge graph", tone: "text-cyan-ink" },
  threat_intel: { title: "Checked threat intelligence", tone: "text-cyan-ink" },
  planner_decision: { title: "Planner chose the next step", tone: "text-lav-ink" },
  action_execution: { title: "Carried that step out", tone: "text-lav-ink" },
  validation: { title: "Checked the findings", tone: "text-mint-ink" },
  outcome_synthesis: { title: "Wrote the recommendation", tone: "text-pear-ink" },
  loop_outcome: { title: "Run finished", tone: "text-ink-2" },
  analyst_note: { title: "Analyst note", tone: "text-ink-2" },
};

// What each terminal condition means for the analyst, in one sentence.
const ENDINGS: Record<string, { readonly tone: string; readonly note: string }> = {
  completed: {
    tone: "text-mint-ink",
    note: "The planner decided it had enough and stopped on its own.",
  },
  escalated: {
    tone: "text-amber-ink",
    note: "The run stopped safely and handed the case back to you. Nothing was lost.",
  },
  exhausted: {
    tone: "text-amber-ink",
    note: "The planner used its whole step budget without reaching a conclusion.",
  },
};

/** Seconds since `active` became true; resets each time a run starts. */
function useElapsedSeconds(active: boolean): number {
  const [seconds, setSeconds] = useState(0);
  useEffect(() => {
    if (!active) {
      setSeconds(0);
      return;
    }
    const started = Date.now();
    const timer = window.setInterval(
      () => setSeconds(Math.round((Date.now() - started) / 1000)),
      1000,
    );
    return () => window.clearInterval(timer);
  }, [active]);
  return seconds;
}

/**
 * What the analyst sees while a run is in flight.
 *
 * A run makes several provider calls in sequence and can take minutes; the
 * request carries no progress, and the trace only becomes readable once the
 * run's transaction commits. A bare spinner for that long reads as a hang, so
 * the wait is made legible: elapsed time, the steps in order, and an explicit
 * statement that leaving the page does not cancel the work.
 */
function RunProgress({ seconds }: { readonly seconds: number }) {
  const minutes = Math.floor(seconds / 60);
  const rest = String(seconds % 60).padStart(2, "0");
  return (
    <div
      role="status"
      className="rise rounded-card border border-lav/45 bg-lav/10 p-4"
    >
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
        <span className="pulse" aria-hidden="true" />
        <span className="text-sm font-semibold">The agents are working</span>
        <span className="mono-label tabular-nums text-ink-2">
          {minutes}:{rest} elapsed
        </span>
      </div>
      <p className="mt-2 text-[0.8125rem] leading-relaxed text-ink-2">
        Gathering context, reading the graph, checking threat intelligence, then
        planning — each step is a separate model call, so a run usually takes
        minutes rather than seconds. The whole reasoning trail appears here at
        once when the run commits.
      </p>
      <p className="mt-1.5 text-xs text-ink-3">
        You can leave this tab; the run continues on the server.
      </p>
    </div>
  );
}

function RunEnding({ outcome }: { readonly outcome: RunOutcomeViewModel }) {
  const ending = ENDINGS[outcome.end];
  return (
    <div
      role="status"
      data-testid="run-outcome"
      className="rise rounded-input border border-line-2 bg-paper px-3.5 py-3"
    >
      <p className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
        <span className={`text-sm font-bold ${ending?.tone ?? "text-ink"}`}>
          {outcome.end}
        </span>
        <span className="mono-label tabular-nums text-ink-3">
          after {outcome.cycles} cycle{outcome.cycles === 1 ? "" : "s"}
        </span>
        {outcome.failureCode !== null && (
          <span className="mono-label text-ink-3">· {outcome.failureCode}</span>
        )}
      </p>
      {ending && (
        <p className="mt-1 text-xs leading-relaxed text-ink-2">{ending.note}</p>
      )}
    </div>
  );
}

function SynthesizedOutcomePanel({
  outcome,
}: {
  readonly outcome: OutcomeViewModel;
}) {
  const percent = Math.round(outcome.confidence * 100);
  return (
    <div
      data-testid="synthesized-outcome"
      className="rise rounded-card border border-pear/50 bg-pear/12 p-4"
    >
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="text-sm font-bold">What the platform recommends</h3>
        <span className="mono-label tabular-nums text-ink-2">
          confidence {percent}%
        </span>
      </div>
      <p className="mt-2 text-[0.9375rem] leading-relaxed">
        {outcome.recommendation}
      </p>

      {outcome.detectedConflicts.length > 0 && (
        <p className="mt-3 border-t border-pear/40 pt-3 text-[0.8125rem] leading-relaxed text-amber-ink">
          Conflicts: {outcome.detectedConflicts.join("; ")}
        </p>
      )}

      {outcome.openQuestions.length > 0 && (
        <p className="mt-3 border-t border-pear/40 pt-3 text-[0.8125rem] leading-relaxed text-ink-2">
          Open questions: {outcome.openQuestions.join("; ")}
        </p>
      )}

      <p className="mt-3 text-xs text-ink-3">
        This is a recommendation, not a decision. Accepting, rejecting or
        escalating it stays with you.
      </p>
    </div>
  );
}

export function AiInsightsSection({ investigationId }: AiInsightsSectionProps) {
  const trace = useInvestigationTrace(investigationId);
  const runState = useRunInvestigation(investigationId);
  const synthesized = useInvestigationOutcome(investigationId);
  const elapsed = useElapsedSeconds(runState.running);

  return (
    <WorkspaceRegion
      title="AI Insights"
      tone="ai"
      note="Every step the agents take is recorded here as it happens — what was read, what was decided, and why the run ended the way it did."
      action={
        <Button
          variant="primary"
          onClick={runState.run}
          busy={runState.running}
        >
          {runState.running ? "Running…" : "Run investigation"}
        </Button>
      }
    >
      <div className="grid gap-4">
        {runState.running && <RunProgress seconds={elapsed} />}

        {runState.outcome && <RunEnding outcome={runState.outcome} />}

        {synthesized.outcome && (
          <SynthesizedOutcomePanel outcome={synthesized.outcome} />
        )}

        {runState.error && (
          <p
            role="alert"
            className="rounded-input border border-coral/50 bg-coral/10 px-3 py-2 text-[0.8125rem] text-coral-ink"
          >
            Run failed ({runState.error.code}): {runState.error.message}
          </p>
        )}

        {trace.error && (
          <p
            role="alert"
            className="rounded-input border border-coral/50 bg-coral/10 px-3 py-2 text-[0.8125rem] text-coral-ink"
          >
            Could not load the trace ({trace.error.code}).
            <Button variant="link" className="ml-2" onClick={trace.retry}>
              Retry
            </Button>
          </p>
        )}

        {trace.loading && (
          <div role="status" className="grid gap-2">
            <span className="sr-only">Loading trace…</span>
            <div className="skeleton h-12 w-full" aria-hidden="true" />
            <div className="skeleton h-12 w-4/5" aria-hidden="true" />
          </div>
        )}

        {!trace.loading && !trace.error && trace.entries.length === 0 && (
          <p className="rounded-input border border-dashed border-line-2 px-4 py-6 text-center text-sm leading-relaxed text-ink-2">
            No AI activity yet. Run the investigation and every step the agents
            take will appear here, in order, in plain language.
          </p>
        )}

        {trace.entries.length > 0 && (
          <ol className="grid max-h-[26rem] gap-2 overflow-y-auto pr-1">
            {trace.entries.map((entry) => {
              const step = STEP[entry.kind];
              return (
                <li key={entry.id} className="card p-3.5">
                  <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
                    <span
                      className={`text-sm font-semibold ${step?.tone ?? "text-ink"}`}
                    >
                      {step?.title ?? entry.kind}
                    </span>
                    <span className="mono-label text-ink-3">{entry.actor}</span>
                  </div>
                  <p className="mt-1.5 text-[0.8125rem] leading-relaxed text-ink-2">
                    {entry.summary}
                  </p>
                  <p className="mono-label mt-1.5 text-ink-3">{entry.kind}</p>
                </li>
              );
            })}
          </ol>
        )}
      </div>
    </WorkspaceRegion>
  );
}
