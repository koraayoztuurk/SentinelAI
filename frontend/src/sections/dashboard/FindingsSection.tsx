// Findings section (dashboard-architecture §5).
//
// Highlights confirmed investigation findings only (the view model already filters
// to validated/accepted). Supporting evidence stays in dedicated workspace regions.

import type { ConfirmedFindingViewModel } from "../../communication/dashboard";
import { FindingCard } from "../../components/dashboard/FindingCard";
import { Empty } from "../../ui/Region";
import { DashboardSection } from "./DashboardSection";

export interface FindingsSectionProps {
  readonly findings: readonly ConfirmedFindingViewModel[];
}

export function FindingsSection({ findings }: FindingsSectionProps) {
  return (
    <DashboardSection
      title="Findings"
      note="Only confirmed conclusions appear here. Proposed and rejected ones stay in the workspace."
    >
      {findings.length === 0 ? (
        <Empty>No confirmed findings yet.</Empty>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {findings.map((finding) => (
            <FindingCard key={finding.id} finding={finding} />
          ))}
        </div>
      )}
    </DashboardSection>
  );
}
