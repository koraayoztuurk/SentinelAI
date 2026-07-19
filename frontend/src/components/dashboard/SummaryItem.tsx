// Summary item component: a labelled value pair used by the investigation summary.

import type { ReactNode } from "react";

export interface SummaryItemProps {
  readonly label: string;
  readonly children: ReactNode;
}

export function SummaryItem({ label, children }: SummaryItemProps) {
  return (
    <div className="border-l border-line pl-3">
      <dt className="mono-label uppercase text-faint">{label}</dt>
      <dd className="mt-1 text-sm text-ink">{children}</dd>
    </div>
  );
}
