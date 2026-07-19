// Workspace finding card component.
//
// A selectable projection of a confirmed finding. Selecting it drives the
// finding→evidence highlight in the Evidence Region through the shared Investigation
// Context. It reuses the dashboard's StatusBadge and ConfidenceIndicator rather than
// redefining them (the dashboard's own FindingCard is non-interactive and stays
// untouched).

import type { ConfirmedFindingViewModel } from "../../communication/dashboard";
import { ConfidenceIndicator } from "../dashboard/ConfidenceIndicator";
import { StatusBadge } from "../dashboard/StatusBadge";

export interface WorkspaceFindingCardProps {
  readonly finding: ConfirmedFindingViewModel;
  readonly selected: boolean;
  readonly onSelect: (findingId: string) => void;
}

export function WorkspaceFindingCard({
  finding,
  selected,
  onSelect,
}: WorkspaceFindingCardProps) {
  return (
    <button
      type="button"
      aria-pressed={selected}
      onClick={() => onSelect(finding.id)}
      className={`card w-full cursor-pointer p-4 text-left ${
        selected ? "card-selected" : ""
      }`}
    >
      <div className="flex items-center justify-between gap-3">
        <span className="mono-label min-w-0 truncate text-faint" title={finding.id}>
          {finding.id}
        </span>
        <StatusBadge status={finding.status} />
      </div>
      <div className="mt-3">
        <ConfidenceIndicator value={finding.confidence} />
      </div>
      <p className="mono-label mt-3 text-faint">by {finding.creator}</p>
    </button>
  );
}
