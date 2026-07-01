// Investigation Workspace page.
//
// The primary operational environment for an investigation
// (investigation-workspace). It resolves the investigation id from the route, loads
// the workspace view model and renders the coordinated regions inside a shared
// Investigation Context provider. Loading, error and empty states preserve the
// investigation context (Frontend Architecture §11). The page binds only to the view
// model — never to backend DTOs.
//
// Regions with no investigation-scoped backend source (AI Insights, Memory) render
// placeholders, and the Graph region is delivered by Graph Visualization (ES-026).

import { Link, useParams } from "react-router-dom";
import { Button } from "../ui/Button";
import { useInvestigationWorkspace } from "../state/useInvestigationWorkspace";
import { WorkspaceProvider } from "../state/workspaceContext";
import { OverviewSection } from "../sections/workspace/OverviewSection";
import { EvidenceSection } from "../sections/workspace/EvidenceSection";
import { FindingsSection } from "../sections/workspace/FindingsSection";
import { TimelineSection } from "../sections/workspace/TimelineSection";
import { GraphSection } from "../sections/workspace/GraphSection";
import { PlaceholderRegion } from "../sections/workspace/WorkspaceRegion";
import type { WorkspaceViewModel } from "../communication/workspace";

function WorkspaceSkeleton() {
  return (
    <p role="status" className="text-sm opacity-60">
      Loading workspace…
    </p>
  );
}

function WorkspaceContent({ viewModel }: { readonly viewModel: WorkspaceViewModel }) {
  return (
    <WorkspaceProvider>
      <div className="grid gap-5">
        <OverviewSection summary={viewModel.summary} />
        <div className="grid gap-5 lg:grid-cols-2">
          <FindingsSection findings={viewModel.findings} />
          <EvidenceSection
            evidence={viewModel.evidence}
            findingEvidence={viewModel.findingEvidence}
          />
        </div>
        <TimelineSection timeline={viewModel.timeline} />
        <GraphSection seedEntities={viewModel.seedEntities} />
        <div className="grid gap-5 md:grid-cols-2">
          <PlaceholderRegion title="AI Insights" />
          <PlaceholderRegion title="Memory" />
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
      <header className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">Investigation Workspace</h1>
          <Link
            to={`/investigations/${id}`}
            className="text-xs opacity-60 hover:opacity-100"
          >
            ← Dashboard
          </Link>
        </div>
        <span className="font-mono text-xs opacity-60">{id}</span>
      </header>

      {loading && <WorkspaceSkeleton />}

      {error && (
        <div role="alert" className="rounded-lg border border-red-500/40 p-5">
          <p className="text-sm">Could not load the investigation ({error.code}).</p>
          <p className="mt-1 text-xs opacity-60">{error.message}</p>
          <Button
            className="mt-3 rounded border border-white/20 px-3 py-1 text-sm"
            onClick={retry}
          >
            Retry
          </Button>
        </div>
      )}

      {viewModel && <WorkspaceContent viewModel={viewModel} />}
    </div>
  );
}
