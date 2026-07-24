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

import { useState } from "react";
import type { InvestigationSummaryViewModel } from "../../communication/dashboard";
import { StatusBadge } from "../../components/dashboard/StatusBadge";
import { SummaryItem } from "../../components/dashboard/SummaryItem";
import { useEraseInvestigation } from "../../state/useEraseInvestigation";
import { Button } from "../../ui/Button";
import { WorkspaceRegion } from "./WorkspaceRegion";

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

  return (
    <section className="mt-5 border-t border-line pt-4">
      <h4 className="mono-label uppercase text-faint">Data lifecycle</h4>

      {summary.erased ? (
        <p className="mt-2 text-sm text-danger">
          This investigation was erased
          {summary.erasedAt ? ` on ${summary.erasedAt}` : ""}. Its data has been
          tombstoned; personal content is redacted and cannot be recovered.
        </p>
      ) : (
        <div className="mt-2 grid gap-2">
          <p className="text-xs text-muted">
            Erasing removes this investigation and cascades to its evidence,
            findings, report, outcome and trace; payload bytes and derived
            embeddings are erased in the background. Retention durations are
            governed by deployment policy. This action cannot be undone.
          </p>
          {confirming ? (
            <div
              className="flex flex-wrap items-center gap-2 rounded-md border border-danger/40 bg-danger/5 p-3"
              role="group"
              aria-label="Confirm erasure"
            >
              <span className="text-sm text-danger">
                Permanently erase this investigation and all its data?
              </span>
              <Button
                className="btn btn-primary bg-danger/80 hover:bg-danger"
                onClick={erase}
                disabled={erasing}
              >
                {erasing ? "Erasing…" : "Confirm erase"}
              </Button>
              <Button
                className="btn btn-ghost"
                onClick={() => setConfirming(false)}
                disabled={erasing}
              >
                Cancel
              </Button>
            </div>
          ) : (
            <div>
              <Button
                className="btn btn-ghost text-danger"
                onClick={() => setConfirming(true)}
              >
                Erase investigation
              </Button>
            </div>
          )}
          {error && (
            <p role="alert" className="text-xs text-danger">
              Could not erase the investigation ({error.code}).
            </p>
          )}
        </div>
      )}
    </section>
  );
}

export function OverviewSection({
  investigationId,
  summary,
}: OverviewSectionProps) {
  return (
    <WorkspaceRegion title="Investigation Overview">
      <h3 className="text-lg font-semibold">{summary.title}</h3>
      <dl className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-3">
        <SummaryItem label="Status">
          <StatusBadge status={summary.status} />
        </SummaryItem>
        <SummaryItem label="Priority">{summary.priority}</SummaryItem>
        <SummaryItem label="Owner">{summary.owner}</SummaryItem>
        <SummaryItem label="Tenant">{summary.tenant}</SummaryItem>
        <SummaryItem label="Identifier">
          <span className="font-mono text-xs">{summary.id}</span>
        </SummaryItem>
        <SummaryItem label="Created">{summary.createdAt}</SummaryItem>
      </dl>
      <DataLifecycle investigationId={investigationId} summary={summary} />
    </WorkspaceRegion>
  );
}
