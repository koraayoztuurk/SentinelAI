// Findings section (dashboard-architecture §5).
//
// Highlights confirmed investigation findings only (the view model already filters
// to validated/accepted). Supporting evidence stays in dedicated workspace regions.

import type { ConfirmedFindingViewModel } from "../../communication/dashboard";
import { FindingCard } from "../../components/dashboard/FindingCard";
import { DashboardSection } from "./DashboardSection";

export interface FindingsSectionProps {
  readonly findings: readonly ConfirmedFindingViewModel[];
}

export function FindingsSection({ findings }: FindingsSectionProps) {
  return (
    <DashboardSection title="Findings">
      {findings.length === 0 ? (
        <p className="text-sm opacity-50">No confirmed findings yet.</p>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2">
          {findings.map((finding) => (
            <FindingCard key={finding.id} finding={finding} />
          ))}
        </div>
      )}
    </DashboardSection>
  );
}
