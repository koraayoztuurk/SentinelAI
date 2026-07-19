// Workspace region shell: a titled region used by every workspace region
// (the workspace counterpart of the dashboard's DashboardSection). Regions stay
// loosely coupled (investigation-workspace §5) — this only provides consistent
// framing.

import type { ReactNode } from "react";

export interface WorkspaceRegionProps {
  readonly title: string;
  readonly children: ReactNode;
}

export function WorkspaceRegion({ title, children }: WorkspaceRegionProps) {
  return (
    <section className="panel p-5">
      <h2 className="panel-title">{title}</h2>
      <div className="mt-4">{children}</div>
    </section>
  );
}

export interface PlaceholderRegionProps {
  readonly title: string;
  readonly note?: string;
}

// Regions whose data source is not yet available (AI Insights, Memory) or that are
// delivered by a later specification (Graph Visualization, ES-026).
export function PlaceholderRegion({ title, note }: PlaceholderRegionProps) {
  return (
    <WorkspaceRegion title={title}>
      <p className="text-sm text-faint">{note ?? "Not yet available."}</p>
    </WorkspaceRegion>
  );
}
