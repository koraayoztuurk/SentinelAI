// Summary item component: a labelled value pair used by the investigation summary.

import type { ReactNode } from "react";

export interface SummaryItemProps {
  readonly label: string;
  readonly children: ReactNode;
}

export function SummaryItem({ label, children }: SummaryItemProps) {
  return (
    <div className="min-w-0 rounded-input bg-paper-2 px-3 py-2.5">
      <dt className="mono-label uppercase text-ink-3">{label}</dt>
      <dd className="mt-1.5 text-sm font-medium text-ink">{children}</dd>
    </div>
  );
}
