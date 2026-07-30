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
    <DashboardSection
      title="Investigation Summary"
      note="Who owns this case, how urgent it is, and where it sits in its lifecycle."
    >
      <dl className="grid grid-cols-2 gap-2.5 sm:grid-cols-3">
        <SummaryItem label="Status">
          <StatusBadge status={summary.status} />
        </SummaryItem>
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
    </DashboardSection>
  );
}
