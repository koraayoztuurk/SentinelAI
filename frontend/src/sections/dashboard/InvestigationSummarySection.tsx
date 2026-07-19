// Investigation Summary section (dashboard-architecture §5/§6).
//
// The highest-level overview of the investigation: identifier, title, status,
// priority, owner and creation time.

import type { InvestigationSummaryViewModel } from "../../communication/dashboard";
import { StatusBadge } from "../../components/dashboard/StatusBadge";
import { SummaryItem } from "../../components/dashboard/SummaryItem";
import { DashboardSection } from "./DashboardSection";

export interface InvestigationSummarySectionProps {
  readonly summary: InvestigationSummaryViewModel;
}

export function InvestigationSummarySection({
  summary,
}: InvestigationSummarySectionProps) {
  return (
    <DashboardSection title="Investigation Summary">
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
    </DashboardSection>
  );
}
