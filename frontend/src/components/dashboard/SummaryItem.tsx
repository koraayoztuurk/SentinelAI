// Summary item component: a labelled value pair used by the investigation summary.

import type { ReactNode } from "react";

export interface SummaryItemProps {
  readonly label: string;
  readonly children: ReactNode;
}

export function SummaryItem({ label, children }: SummaryItemProps) {
  return (
    <div>
      <dt className="text-xs uppercase tracking-wide opacity-60">{label}</dt>
      <dd className="mt-1 text-sm">{children}</dd>
    </div>
  );
}
