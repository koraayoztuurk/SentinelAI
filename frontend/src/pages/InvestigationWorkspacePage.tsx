// Investigation Workspace page.
//
// The primary operational environment for an investigation
// (investigation-workspace). It resolves the investigation id from the route, loads
// the workspace view model and renders the coordinated regions inside a shared
// Investigation Context provider. Loading, error and empty states preserve the
// investigation context (Frontend Architecture §11). The page binds only to the
// view model — never to backend DTOs.
//
// The regions are grouped into tabs rather than stacked into one long scroll.
// Eight regions on one page asks the analyst to hold the whole platform in
// their head at once; six named tabs ask them to hold one question at a time.
// Panels stay mounted, so a graph exploration or a selected finding survives a
// trip to another tab and the cross-region highlighting keeps working.

import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Button } from "../ui/Button";
import { Disclosure } from "../ui/Disclosure";
import { Tabs, type TabDefinition } from "../ui/Tabs";
import { useInvestigationWorkspace } from "../state/useInvestigationWorkspace";
import { useRememberInvestigation } from "../state/useRememberInvestigation";
import { WorkspaceProvider } from "../state/workspaceContext";
import { StatusBadge } from "../components/dashboard/StatusBadge";
import { OverviewSection } from "../sections/workspace/OverviewSection";
import { AiInsightsSection } from "../sections/workspace/AiInsightsSection";
import { EvidenceSection } from "../sections/workspace/EvidenceSection";
import { FindingsSection } from "../sections/workspace/FindingsSection";
import { TimelineSection } from "../sections/workspace/TimelineSection";
import { GraphSection } from "../sections/workspace/GraphSection";
import { MemorySection } from "../sections/workspace/MemorySection";
import { PlatformSection } from "../sections/workspace/PlatformSection";
import type { WorkspaceViewModel } from "../communication/workspace";

// Tab labels deliberately differ from the region headings inside them: the tab
// answers "where do I go", the heading answers "what is this".
const TAB_OVERVIEW = "overview";
const TAB_EVIDENCE = "evidence";
const TAB_AI = "ai";
const TAB_GRAPH = "graph";
const TAB_KNOWLEDGE = "knowledge";
const TAB_PLATFORM = "platform";

function WorkspaceSkeleton() {
  return (
    <div role="status" className="grid gap-5">
      <span className="sr-only">Loading workspace…</span>
      <div className="skeleton h-28 w-full" aria-hidden="true" />
      <div className="skeleton h-12 w-2/3" aria-hidden="true" />
      <div className="skeleton h-72 w-full" aria-hidden="true" />
    </div>
  );
}

function Primer() {
  return (
    <Disclosure
      className="surface surface-quiet p-4"
      summary="New here? What this workspace is"
    >
      <div className="grid gap-2.5 text-[0.8125rem] leading-relaxed text-ink-2 sm:grid-cols-2">
        <p>
          <span className="font-semibold text-ink">Evidence</span> is what you
          observed and never changes. A{" "}
          <span className="font-semibold text-ink">finding</span> is a conclusion
          you or an agent drew from it, and it always points back at the evidence
          underneath.
        </p>
        <p>
          <span className="font-semibold text-ink">AI analysis</span> runs the
          agents over the case and writes down every step. Nothing is decided for
          you — you get a recommendation with its confidence, its conflicts and
          its open questions.
        </p>
        <p>
          <span className="font-semibold text-ink">Graph</span> shows how the
          people, machines and addresses in this case connect.{" "}
          <span className="font-semibold text-ink">Knowledge</span> is what this
          case teaches the organisation for next time.
        </p>
        <p>
          <span className="font-semibold text-ink">Platform</span> is the tool
          reporting on itself: which stores are healthy, whether its audit log is
          tamper-evident, and how it handles data at end of life.
        </p>
      </div>
    </Disclosure>
  );
}

function WorkspaceContent({
  investigationId,
  viewModel,
}: {
  readonly investigationId: string;
  readonly viewModel: WorkspaceViewModel;
}) {
  const [active, setActive] = useState(TAB_OVERVIEW);

  const tabs: readonly TabDefinition[] = [
    { id: TAB_OVERVIEW, label: "Overview" },
    {
      id: TAB_EVIDENCE,
      label: "Evidence",
      count: viewModel.evidence.length + viewModel.findings.length,
    },
    { id: TAB_AI, label: "AI analysis" },
    { id: TAB_GRAPH, label: "Graph view", count: viewModel.seedEntities.length },
    { id: TAB_KNOWLEDGE, label: "Knowledge" },
    { id: TAB_PLATFORM, label: "Platform" },
  ];

  return (
    <WorkspaceProvider>
      <Tabs
        tabs={tabs}
        active={active}
        onChange={setActive}
        label="Investigation workspace sections"
      >
        {(tabId) => {
          switch (tabId) {
            case TAB_OVERVIEW:
              return (
                <div className="rise-seq grid gap-5">
                  <OverviewSection
                    investigationId={investigationId}
                    summary={viewModel.summary}
                  />
                  <TimelineSection timeline={viewModel.timeline} />
                </div>
              );
            case TAB_EVIDENCE:
              return (
                <div className="rise-seq grid gap-5">
                  <FindingsSection
                    findings={viewModel.findings}
                    investigationId={investigationId}
                    evidence={viewModel.evidence}
                  />
                  <EvidenceSection
                    investigationId={investigationId}
                    evidence={viewModel.evidence}
                    findingEvidence={viewModel.findingEvidence}
                  />
                </div>
              );
            case TAB_AI:
              return (
                <div className="rise">
                  <AiInsightsSection investigationId={investigationId} />
                </div>
              );
            case TAB_GRAPH:
              return (
                <div className="rise">
                  <GraphSection seedEntities={viewModel.seedEntities} />
                </div>
              );
            case TAB_KNOWLEDGE:
              return (
                <div className="rise">
                  <MemorySection
                    investigationId={investigationId}
                    findings={viewModel.findings}
                  />
                </div>
              );
            default:
              return (
                <div className="rise">
                  <PlatformSection />
                </div>
              );
          }
        }}
      </Tabs>
    </WorkspaceProvider>
  );
}

export function InvestigationWorkspacePage() {
  const { id = "" } = useParams();
  const { viewModel, loading, error, retry } = useInvestigationWorkspace(id);
  // Opening a case is what puts it on the home page's recent list; there is no
  // server-side investigation list to read one from.
  useRememberInvestigation(id, viewModel?.summary.title);

  return (
    <div className="grid min-w-0 gap-6">
      <header className="rise grid min-w-0 gap-4">
        <div className="flex flex-wrap items-start justify-between gap-x-6 gap-y-3">
          <div className="min-w-0">
            <p className="eyebrow">Investigation</p>
            <h1 className="mt-1.5 max-w-3xl text-[clamp(1.5rem,3.2vw,2.125rem)] font-bold leading-tight">
              {viewModel ? viewModel.summary.title : "Investigation workspace"}
            </h1>
            <div className="mt-2.5 flex flex-wrap items-center gap-2">
              {viewModel && <StatusBadge status={viewModel.summary.status} />}
              <span className="mono-label min-w-0 break-all text-ink-3">
                {id}
              </span>
            </div>
          </div>
          <Link to={`/investigations/${id}`} className="link shrink-0 text-sm">
            Summary view
          </Link>
        </div>
        {viewModel && <Primer />}
      </header>

      {loading && <WorkspaceSkeleton />}

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
        <WorkspaceContent investigationId={id} viewModel={viewModel} />
      )}
    </div>
  );
}
