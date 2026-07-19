// Investigation Overview region (investigation-workspace §5).
//
// A high-level summary of the current investigation: identifier, title, status,
// priority, owner and creation time. Presentation only; it reuses the shared summary
// view model (`InvestigationSummaryViewModel`) rather than redefining it.

import type { InvestigationSummaryViewModel } from "../../communication/dashboard";
import { StatusBadge } from "../../components/dashboard/StatusBadge";
import { SummaryItem } from "../../components/dashboard/SummaryItem";
import { WorkspaceRegion } from "./WorkspaceRegion";

export interface OverviewSectionProps {
  readonly summary: InvestigationSummaryViewModel;
}

export function OverviewSection({ summary }: OverviewSectionProps) {
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
    </WorkspaceRegion>
  );
}
