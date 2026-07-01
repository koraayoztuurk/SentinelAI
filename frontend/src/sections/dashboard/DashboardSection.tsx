// Dashboard section shell: a titled region used by every dashboard component.

import type { ReactNode } from "react";

export interface DashboardSectionProps {
  readonly title: string;
  readonly children: ReactNode;
}

export function DashboardSection({ title, children }: DashboardSectionProps) {
  return (
    <section className="rounded-xl border border-white/10 bg-white/5 p-5">
      <h2 className="text-sm font-semibold uppercase tracking-wide opacity-70">
        {title}
      </h2>
      <div className="mt-4">{children}</div>
    </section>
  );
}

export interface PlaceholderSectionProps {
  readonly title: string;
}

// Sections whose backend data source is not yet available (Active Objectives,
// AI Insights, Recent Activity). They render an explicit empty state and are
// connected to real data by later specifications.
export function PlaceholderSection({ title }: PlaceholderSectionProps) {
  return (
    <DashboardSection title={title}>
      <p className="text-sm opacity-50">Not yet available.</p>
    </DashboardSection>
  );
}
