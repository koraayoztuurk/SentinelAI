// Dashboard view model + loader.
//
// The communication layer maps backend DTOs into a UI-oriented
// `DashboardViewModel` so the dashboard page never depends on backend DTO shapes
// (the frontend counterpart of the backend's to_domain/from_domain mappers). Field
// selection, the confirmed-findings filter and camelCase normalization all happen
// here, in one place.

import {
  getInvestigation,
  listFindings,
  type FindingDto,
  type InvestigationDto,
} from "./investigations";

export interface InvestigationSummaryViewModel {
  readonly id: string;
  readonly title: string;
  readonly status: string;
  readonly priority: string;
  readonly owner: string;
  readonly createdAt: string;
}

export interface ConfirmedFindingViewModel {
  readonly id: string;
  readonly status: string;
  readonly confidence: number;
  readonly creator: string;
  readonly createdAt: string;
}

export interface DashboardViewModel {
  readonly summary: InvestigationSummaryViewModel;
  readonly findings: readonly ConfirmedFindingViewModel[];
}

// Only confirmed findings appear on the dashboard (dashboard-architecture §5).
const CONFIRMED_STATUSES = new Set(["validated", "accepted"]);

// A finding is confirmed when it has been validated or accepted. Shared so other
// investigation-scoped derivations (e.g. graph seeds, ES-026) classify findings the
// same way the dashboard does.
export function isConfirmedFinding(status: string): boolean {
  return CONFIRMED_STATUSES.has(status);
}

export function toDashboardViewModel(
  investigation: InvestigationDto,
  findings: readonly FindingDto[],
): DashboardViewModel {
  return {
    summary: {
      id: investigation.id,
      title: investigation.title,
      status: investigation.status,
      priority: investigation.priority,
      owner: investigation.owner,
      createdAt: investigation.created_at,
    },
    findings: findings
      .filter((finding) => isConfirmedFinding(finding.status))
      .map((finding) => ({
        id: finding.id,
        status: finding.status,
        confidence: finding.confidence,
        creator: finding.creator,
        createdAt: finding.created_at,
      })),
  };
}

export async function loadInvestigationDashboard(
  id: string,
  signal?: AbortSignal,
): Promise<DashboardViewModel> {
  const [investigation, findings] = await Promise.all([
    getInvestigation(id, signal),
    listFindings(id, signal),
  ]);
  return toDashboardViewModel(investigation, findings);
}
