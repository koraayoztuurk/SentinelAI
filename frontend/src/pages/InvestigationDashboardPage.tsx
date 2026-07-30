// Investigation Dashboard page.
//
// The summary layer of the Investigation Workspace (dashboard-architecture). It
// resolves the investigation id from the route, loads the dashboard view model and
// renders the six dashboard components. Loading, error and empty states preserve
// the investigation context (Frontend Architecture §11). The page binds only to the
// view model — never to backend DTOs.
//
// This page answers "where does this case stand"; the workspace answers "what do
// I do about it". The primary action here is therefore opening the workspace,
// not editing anything in place.

import { Link, useParams } from "react-router-dom";
import { Button } from "../ui/Button";
import { useInvestigationDashboard } from "../state/useInvestigationDashboard";
import { useRememberInvestigation } from "../state/useRememberInvestigation";
import { StatusBadge } from "../components/dashboard/StatusBadge";
import { InvestigationSummarySection } from "../sections/dashboard/InvestigationSummarySection";
import { FindingsSection } from "../sections/dashboard/FindingsSection";
import { PlaceholderSection } from "../sections/dashboard/DashboardSection";

function DashboardSkeleton() {
  return (
    <div role="status" className="grid gap-5">
      <span className="sr-only">Loading investigation…</span>
      <div className="skeleton h-44 w-full" aria-hidden="true" />
      <div className="skeleton h-56 w-full" aria-hidden="true" />
      <div className="grid gap-5 md:grid-cols-3" aria-hidden="true">
        <div className="skeleton h-28" />
        <div className="skeleton h-28" />
        <div className="skeleton h-28" />
      </div>
    </div>
  );
}

export function InvestigationDashboardPage() {
  const { id = "" } = useParams();
  const { viewModel, loading, error, retry } = useInvestigationDashboard(id);
  useRememberInvestigation(id, viewModel?.summary.title);

  return (
    <div className="grid gap-6">
      <header className="rise flex flex-wrap items-start justify-between gap-x-6 gap-y-4">
        <div className="min-w-0">
          <p className="eyebrow">Case summary</p>
          <h1 className="mt-1.5 max-w-3xl text-[clamp(1.5rem,3.2vw,2.125rem)] font-bold leading-tight">
            {viewModel ? viewModel.summary.title : "Investigation"}
          </h1>
          <div className="mt-2.5 flex flex-wrap items-center gap-2">
            {viewModel && <StatusBadge status={viewModel.summary.status} />}
            <span className="mono-label text-ink-3">{id}</span>
          </div>
        </div>
        <Link
          to={`/investigations/${id}/workspace`}
          className="btn no-underline"
        >
          Open workspace
        </Link>
      </header>

      {loading && <DashboardSkeleton />}

      {error && (
        <div
          role="alert"
          className="rise rounded-card border border-coral/50 bg-coral/10 p-5"
        >
          <p className="text-sm font-semibold text-coral-ink">
            Could not load the investigation ({error.code}).
          </p>
          <p className="mt-1 text-[0.8125rem] text-ink-2">{error.message}</p>
          <Button variant="soft" className="btn-sm mt-3" onClick={retry}>
            Retry
          </Button>
        </div>
      )}

      {viewModel && (
        <div className="rise-seq grid gap-5">
          <InvestigationSummarySection summary={viewModel.summary} />
          <FindingsSection findings={viewModel.findings} />
          <div className="grid gap-5 md:grid-cols-3">
            <PlaceholderSection
              title="Active Objectives"
              note="Objectives are derived from the case title today; a dedicated source is a later step."
            />
            <PlaceholderSection
              title="AI Insights"
              note="The agents' reasoning lives in the workspace, under AI analysis."
            />
            <PlaceholderSection
              title="Recent Activity"
              note="The full ordered history is in the workspace timeline."
            />
          </div>
        </div>
      )}
    </div>
  );
}
