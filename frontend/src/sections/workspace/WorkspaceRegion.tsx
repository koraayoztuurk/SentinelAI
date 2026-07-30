// Workspace region shell: a titled region used by every workspace region
// (the workspace counterpart of the dashboard's DashboardSection). Regions stay
// loosely coupled (investigation-workspace §5) — this only provides consistent
// framing.
//
// The shell now delegates to the shared `Region` primitive so a region can also
// carry a plain-language note and an accent tone. `note` is optional, which
// keeps every existing call site valid.

import type { ReactNode } from "react";
import { Region, type RegionTone } from "../../ui/Region";

export interface WorkspaceRegionProps {
  readonly title: string;
  readonly note?: string;
  readonly action?: ReactNode;
  readonly tone?: RegionTone;
  readonly children: ReactNode;
}

export function WorkspaceRegion({
  title,
  note,
  action,
  tone,
  children,
}: WorkspaceRegionProps) {
  return (
    <Region title={title} note={note} action={action} tone={tone}>
      {children}
    </Region>
  );
}

export interface PlaceholderRegionProps {
  readonly title: string;
  readonly note?: string;
}

// Regions whose data source is not yet available or that are delivered by a
// later specification.
export function PlaceholderRegion({ title, note }: PlaceholderRegionProps) {
  return (
    <WorkspaceRegion title={title}>
      <p className="text-sm text-ink-2">{note ?? "Not yet available."}</p>
    </WorkspaceRegion>
  );
}
