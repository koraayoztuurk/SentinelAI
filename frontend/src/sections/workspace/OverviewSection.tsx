// Investigation Overview region (investigation-workspace §5).
//
// A high-level summary of the current investigation: identifier, title, status,
// priority, owner and creation time. Presentation only for the summary; it reuses
// the shared summary view model (`InvestigationSummaryViewModel`) rather than
// redefining it.
//
// ES-066 adds the Data Lifecycle control: the analyst can erase the
// investigation (data-lifecycle.md, ADR-017) behind an explicit, irreversible
// confirmation, and a tombstoned investigation renders its erased state
// explicitly (§8a — observable, never hidden). Retention durations are
// deployment policy (§3), so this surface states the posture read-only rather
// than editing configuration the platform does not own.
//
// The destructive control stays visible rather than hidden behind a disclosure:
// an irreversible action the analyst cannot find is not safer, only harder to
// audit. It is separated and quietened instead — outlined, coral, below a rule.

import { useState } from "react";
import type { InvestigationSummaryViewModel } from "../../communication/dashboard";
import { StatusBadge } from "../../components/dashboard/StatusBadge";
import { SummaryItem } from "../../components/dashboard/SummaryItem";
import { useChangeInvestigationStatus } from "../../state/useChangeInvestigationStatus";
import { useEraseInvestigation } from "../../state/useEraseInvestigation";
import { Button } from "../../ui/Button";
import { WorkspaceRegion } from "./WorkspaceRegion";

// The documented business lifecycle (domain-model §15): suspension is
// reversible, completion can be reopened on significant new evidence, archived
// is terminal. This map decides which buttons are *offered*; the Investigation
// Service remains the authority and refuses anything it does not permit, so a
// drift here costs an error message, never a bad write.
const NEXT_STATES: Record<string, readonly string[]> = {
  created: ["active"],
  active: ["suspended", "completed", "archived"],
  suspended: ["active", "archived"],
  completed: ["active", "archived"],
};

const STATE_LABEL: Record<string, string> = {
  active: "Mark active",
  suspended: "Suspend",
  completed: "Mark completed",
  archived: "Archive",
};

function Lifecycle({
  investigationId,
  summary,
}: {
  readonly investigationId: string;
  readonly summary: InvestigationSummaryViewModel;
}) {
  const { change, changing, error } = useChangeInvestigationStatus(
    investigationId,
  );
  const next = NEXT_STATES[summary.status.toLowerCase()] ?? [];

  if (summary.erased || next.length === 0) {
    return null;
  }

  return (
    <section className="mt-5 border-t border-line pt-4">
      <h3 className="mono-label uppercase text-ink-3">Investigation state</h3>
      <p className="mt-1.5 text-xs leading-relaxed text-ink-2">
        Where this case sits in its lifecycle. Suspending is reversible, and a
        completed case can be reopened if significant new evidence arrives.
      </p>
      <div className="mt-3 flex flex-wrap gap-2">
        {next.map((state) => (
          <Button
            key={state}
            variant="soft"
            className="btn-sm"
            onClick={() => change(state)}
            busy={changing}
          >
            {STATE_LABEL[state] ?? state}
          </Button>
        ))}
      </div>
      {error && (
        <p
          role="alert"
          className="mt-3 rounded-input border border-coral/50 bg-coral/10 px-3 py-2 text-xs text-coral-ink"
        >
          Could not change the state ({error.code}).
        </p>
      )}
    </section>
  );
}

export interface OverviewSectionProps {
  readonly investigationId: string;
  readonly summary: InvestigationSummaryViewModel;
}

function DataLifecycle({
  investigationId,
  summary,
}: {
  readonly investigationId: string;
  readonly summary: InvestigationSummaryViewModel;
}) {
  const [confirming, setConfirming] = useState(false);
  const { erase, erasing, error } = useEraseInvestigation(investigationId);

  if (summary.erased) {
    return (
      <section className="mt-6 rounded-card border border-coral/50 bg-coral/10 p-4">
        <h3 className="text-sm font-bold text-coral-ink">Erased</h3>
        <p className="mt-1.5 text-[0.8125rem] leading-relaxed text-ink-2">
          This investigation was erased
          {summary.erasedAt ? ` on ${summary.erasedAt}` : ""}. Its data has been
          tombstoned; personal content is redacted and cannot be recovered. The
          identifiers and timestamps remain so the record of what happened
          survives what it described.
        </p>
      </section>
    );
  }

  return (
    <section className="mt-6 border-t border-line pt-4">
      <h3 className="mono-label uppercase text-ink-3">Data lifecycle</h3>
      <p className="mt-1.5 max-w-2xl text-xs leading-relaxed text-ink-2">
        Erasing removes this investigation and cascades to its evidence,
        findings, report, outcome and trace; payload bytes and derived
        embeddings follow in the background. Retention durations are governed by
        deployment policy. This cannot be undone.
      </p>

      {confirming ? (
        <div
          className="mt-3 flex flex-wrap items-center gap-3 rounded-card border border-coral/50 bg-coral/10 p-3.5"
          role="group"
          aria-label="Confirm erasure"
        >
          <span className="text-sm font-semibold text-coral-ink">
            Permanently erase this investigation and all its data?
          </span>
          <Button
            variant="danger"
            className="btn-sm"
            onClick={erase}
            busy={erasing}
          >
            {erasing ? "Erasing…" : "Confirm erase"}
          </Button>
          <Button
            variant="outline"
            className="btn-sm"
            onClick={() => setConfirming(false)}
            disabled={erasing}
          >
            Cancel
          </Button>
        </div>
      ) : (
        <Button
          variant="outline"
          className="btn-sm mt-3 text-coral-ink"
          onClick={() => setConfirming(true)}
        >
          Erase investigation
        </Button>
      )}

      {error && (
        <p
          role="alert"
          className="mt-3 rounded-input border border-coral/50 bg-coral/10 px-3 py-2 text-xs text-coral-ink"
        >
          Could not erase the investigation ({error.code}).
        </p>
      )}
    </section>
  );
}

export function OverviewSection({
  investigationId,
  summary,
}: OverviewSectionProps) {
  return (
    <WorkspaceRegion
      title="Case details"
      note="Who owns this investigation, what state it is in, and when it started."
      action={<StatusBadge status={summary.status} />}
    >
      <dl className="grid grid-cols-2 gap-2.5 sm:grid-cols-3">
        <SummaryItem label="Priority">{summary.priority}</SummaryItem>
        <SummaryItem label="Owner">{summary.owner}</SummaryItem>
        <SummaryItem label="Tenant">{summary.tenant}</SummaryItem>
        <SummaryItem label="Created">
          <span className="tabular-nums">{summary.createdAt}</span>
        </SummaryItem>
        <SummaryItem label="Identifier">
          <span className="mono-label break-all">{summary.id}</span>
        </SummaryItem>
      </dl>
      <Lifecycle investigationId={investigationId} summary={summary} />
      <DataLifecycle investigationId={investigationId} summary={summary} />
    </WorkspaceRegion>
  );
}
