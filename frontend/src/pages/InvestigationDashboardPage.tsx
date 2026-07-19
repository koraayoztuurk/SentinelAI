// Investigation Dashboard page.
//
// The summary layer of the Investigation Workspace (dashboard-architecture). It
// resolves the investigation id from the route, loads the dashboard view model and
// renders the six dashboard components. Loading, error and empty states preserve
// the investigation context (Frontend Architecture §11). The page binds only to the
// view model — never to backend DTOs.

import { Link, useParams } from "react-router-dom";
import { Button } from "../ui/Button";
import { useInvestigationDashboard } from "../state/useInvestigationDashboard";
import { InvestigationSummarySection } from "../sections/dashboard/InvestigationSummarySection";
import { FindingsSection } from "../sections/dashboard/FindingsSection";
import { PlaceholderSection } from "../sections/dashboard/DashboardSection";

function DashboardSkeleton() {
  return (
    <div role="status" className="grid gap-5">
      <span className="sr-only">Loading investigation…</span>
      <div className="shimmer h-40 w-full" aria-hidden="true" />
      <div className="shimmer h-56 w-full" aria-hidden="true" />
      <div className="grid gap-5 md:grid-cols-3" aria-hidden="true">
        <div className="shimmer h-28" />
        <div className="shimmer h-28" />
        <div className="shimmer h-28" />
      </div>
    </div>
  );
}

export function InvestigationDashboardPage() {
  const { id = "" } = useParams();
  const { viewModel, loading, error, retry } = useInvestigationDashboard(id);

  return (
    <div className="mx-auto max-w-5xl">
      <header className="fade-up mb-6 flex items-end justify-between gap-4">
        <div>
          <p className="mono-label uppercase text-faint">console / summary</p>
          <h1 className="mt-1 text-2xl font-bold tracking-tight">
            Investigation Dashboard
          </h1>
          <Link
            to={`/investigations/${id}/workspace`}
            className="btn-link mono-label mt-1 inline-block"
          >
            Open workspace →
          </Link>
        </div>
        <span className="mono-label rounded-md border border-line bg-panel-2/60 px-2.5 py-1 text-muted">
          {id}
        </span>
      </header>

      {loading && <DashboardSkeleton />}

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
        <div className="stagger grid gap-5">
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
