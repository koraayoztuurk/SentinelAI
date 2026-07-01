// Finding card component (minimal).
//
// Presents a confirmed finding's status, confidence and provenance. Supporting
// evidence remains accessible through dedicated workspace regions (ES-025).

import type { ConfirmedFindingViewModel } from "../../communication/dashboard";
import { ConfidenceIndicator } from "./ConfidenceIndicator";
import { StatusBadge } from "./StatusBadge";

export interface FindingCardProps {
  readonly finding: ConfirmedFindingViewModel;
}

export function FindingCard({ finding }: FindingCardProps) {
  return (
    <article className="rounded-lg border border-white/10 bg-white/5 p-4">
      <div className="flex items-center justify-between gap-3">
        <span className="font-mono text-xs opacity-70">{finding.id}</span>
        <StatusBadge status={finding.status} />
      </div>
      <div className="mt-3">
        <ConfidenceIndicator value={finding.confidence} />
      </div>
      <p className="mt-3 text-xs opacity-60">by {finding.creator}</p>
    </article>
  );
}
