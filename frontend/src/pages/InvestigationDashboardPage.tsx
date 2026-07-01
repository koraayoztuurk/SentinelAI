// Investigation Dashboard page.
//
// The summary layer of the Investigation Workspace (dashboard-architecture). It
// resolves the investigation id from the route, loads the dashboard view model and
// renders the six dashboard components. Loading, error and empty states preserve
// the investigation context (Frontend Architecture §11). The page binds only to the
// view model — never to backend DTOs.

import { useParams } from "react-router-dom";
import { Button } from "../ui/Button";
import { useInvestigationDashboard } from "../state/useInvestigationDashboard";
import { InvestigationSummarySection } from "../sections/dashboard/InvestigationSummarySection";
import { FindingsSection } from "../sections/dashboard/FindingsSection";
import { PlaceholderSection } from "../sections/dashboard/DashboardSection";

function DashboardSkeleton() {
  return (
    <p role="status" className="text-sm opacity-60">
      Loading investigation…
    </p>
  );
}

export function InvestigationDashboardPage() {
  const { id = "" } = useParams();
  const { viewModel, loading, error } = useInvestigationDashboard(id);

  return (
    <div className="mx-auto max-w-5xl">
      <header className="mb-6 flex items-center justify-between">
        <h1 className="text-xl font-semibold">Investigation Dashboard</h1>
        <span className="font-mono text-xs opacity-60">{id}</span>
      </header>

      {loading && <DashboardSkeleton />}

      {error && (
        <div role="alert" className="rounded-lg border border-red-500/40 p-5">
          <p className="text-sm">Could not load the investigation ({error.code}).</p>
          <p className="mt-1 text-xs opacity-60">{error.message}</p>
          <Button
            className="mt-3 rounded border border-white/20 px-3 py-1 text-sm"
            onClick={() => window.location.reload()}
          >
            Retry
          </Button>
        </div>
      )}

      {viewModel && (
        <div className="grid gap-5">
          <InvestigationSummarySection summary={viewModel.summary} />
          <FindingsSection findings={viewModel.findings} />
          <div className="grid gap-5 md:grid-cols-3">
            <PlaceholderSection title="Active Objectives" />
            <PlaceholderSection title="AI Insights" />
            <PlaceholderSection title="Recent Activity" />
          </div>
        </div>
      )}
    </div>
  );
}
