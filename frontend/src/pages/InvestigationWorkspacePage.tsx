// Investigation Workspace page.
//
// The primary operational environment for an investigation
// (investigation-workspace). It resolves the investigation id from the route, loads
// the workspace view model and renders the coordinated regions inside a shared
// Investigation Context provider. Loading, error and empty states preserve the
// investigation context (Frontend Architecture §11). The page binds only to the view
// model — never to backend DTOs.
//
// Every region is live: AI Insights presents the trace + run interaction
// (ES-047), Memory presents the investigation's organizational knowledge
// (ES-052), and the Graph region is delivered by Graph Visualization (ES-026).

import { Link, useParams } from "react-router-dom";
import { Button } from "../ui/Button";
import { useInvestigationWorkspace } from "../state/useInvestigationWorkspace";
import { WorkspaceProvider } from "../state/workspaceContext";
import { OverviewSection } from "../sections/workspace/OverviewSection";
import { AiInsightsSection } from "../sections/workspace/AiInsightsSection";
import { EvidenceSection } from "../sections/workspace/EvidenceSection";
import { FindingsSection } from "../sections/workspace/FindingsSection";
import { TimelineSection } from "../sections/workspace/TimelineSection";
import { GraphSection } from "../sections/workspace/GraphSection";
import { MemorySection } from "../sections/workspace/MemorySection";
import type { WorkspaceViewModel } from "../communication/workspace";

function WorkspaceSkeleton() {
  return (
    <div role="status" className="grid gap-5">
      <span className="sr-only">Loading workspace…</span>
      <div className="shimmer h-40 w-full" aria-hidden="true" />
      <div className="grid gap-5 lg:grid-cols-2" aria-hidden="true">
        <div className="shimmer h-64" />
        <div className="shimmer h-64" />
      </div>
      <div className="shimmer h-32 w-full" aria-hidden="true" />
    </div>
  );
}

function WorkspaceContent({
  investigationId,
  viewModel,
}: {
  readonly investigationId: string;
  readonly viewModel: WorkspaceViewModel;
}) {
  return (
    <WorkspaceProvider>
      <div className="stagger grid gap-5">
        <OverviewSection summary={viewModel.summary} />
        <div className="grid gap-5 lg:grid-cols-2">
          <FindingsSection findings={viewModel.findings} />
          <EvidenceSection
            investigationId={investigationId}
            evidence={viewModel.evidence}
            findingEvidence={viewModel.findingEvidence}
          />
        </div>
        <TimelineSection timeline={viewModel.timeline} />
        <GraphSection seedEntities={viewModel.seedEntities} />
        <div className="grid gap-5 md:grid-cols-2">
          <AiInsightsSection investigationId={investigationId} />
          <MemorySection investigationId={investigationId} />
        </div>
      </div>
    </WorkspaceProvider>
  );
}

export function InvestigationWorkspacePage() {
  const { id = "" } = useParams();
  const { viewModel, loading, error, retry } = useInvestigationWorkspace(id);

  return (
    <div className="mx-auto max-w-6xl">
      <header className="fade-up mb-6 flex items-end justify-between gap-4">
        <div>
          <p className="mono-label uppercase text-faint">console / operations</p>
          <h1 className="mt-1 text-2xl font-bold tracking-tight">
            Investigation Workspace
          </h1>
          <Link
            to={`/investigations/${id}`}
            className="btn-link mono-label mt-1 inline-block"
          >
            ← Dashboard
          </Link>
        </div>
        <span className="mono-label rounded-md border border-line bg-panel-2/60 px-2.5 py-1 text-muted">
          {id}
        </span>
      </header>

      {loading && <WorkspaceSkeleton />}

      {error && (
        <div
          role="alert"
          className="fade-up rounded-lg border border-danger/40 bg-danger/5 p-5"
        >
          <p className="text-sm">Could not load the investigation ({error.code}).</p>
          <p className="mt-1 text-xs text-muted">{error.message}</p>
          <Button className="btn btn-ghost mt-3" onClick={retry}>
            Retry
          </Button>
        </div>
      )}

      {viewModel && (
        <WorkspaceContent investigationId={id} viewModel={viewModel} />
      )}
    </div>
  );
}
