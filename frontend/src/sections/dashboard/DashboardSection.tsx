// Dashboard section shell: a titled region used by every dashboard component.
//
// Delegates to the shared `Region` primitive so dashboard and workspace regions
// stay visually identical without either owning the other's shell.

import type { ReactNode } from "react";
import { Region, type RegionTone } from "../../ui/Region";

export interface DashboardSectionProps {
  readonly title: string;
  readonly note?: string;
  readonly action?: ReactNode;
  readonly tone?: RegionTone;
  readonly children: ReactNode;
}

export function DashboardSection({
  title,
  note,
  action,
  tone,
  children,
}: DashboardSectionProps) {
  return (
    <Region title={title} note={note} action={action} tone={tone}>
      {children}
    </Region>
  );
}

export interface PlaceholderSectionProps {
  readonly title: string;
  readonly note?: string;
}

// Sections whose backend data source is not yet available (Active Objectives,
// Recent Activity). They render an explicit empty state and are connected to
// real data by later specifications.
export function PlaceholderSection({ title, note }: PlaceholderSectionProps) {
  return (
    <DashboardSection title={title}>
      <p className="rounded-input border border-dashed border-line-2 px-3 py-4 text-center text-xs text-ink-3">
        {note ?? "Not connected to a data source yet."}
      </p>
    </DashboardSection>
  );
}
