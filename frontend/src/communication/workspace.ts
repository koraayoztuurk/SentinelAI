// Workspace view model + derivations + loader.
//
// The Investigation Workspace presents several coordinated regions over the same
// investigation (investigation-workspace §4/§5). This module maps the backend DTOs
// into a UI-oriented `WorkspaceViewModel` so the workspace page never depends on
// backend DTO shapes (the frontend counterpart of the backend to_domain/from_domain
// mappers).
//
// The view model extends the ES-024 `DashboardViewModel`: the shared investigation
// `summary` and the confirmed (validated/accepted) `findings` — which the Findings
// Region also presents (investigation-workspace §5, "validated investigation
// findings") — are reused as-is rather than redefined. Only the workspace-specific
// projections are added.
//
// Timeline events and the finding→evidence index are Derived State
// (ui-state-management §5): they are reproducible from the authoritative DTOs, so
// they live in pure, standalone helpers and the mapper only composes them.

import {
  getInvestigation,
  listEvidence,
  listFindings,
  type EvidenceDto,
  type FindingDto,
  type InvestigationDto,
} from "./investigations";
import {
  isConfirmedFinding,
  toDashboardViewModel,
  type DashboardViewModel,
} from "./dashboard";

export interface EvidenceViewModel {
  readonly id: string;
  readonly source: string;
  readonly integrity: string;
  readonly timestamp: string;
  readonly content: string;
}

export type TimelineEventKind = "evidence" | "finding";

export interface TimelineEventViewModel {
  readonly id: string; // stable render key ("evidence:<id>" / "finding:<id>")
  readonly kind: TimelineEventKind;
  readonly reference: string; // the evidence/finding id (for selection highlight)
  readonly label: string;
  readonly occurredAt: string;
}

// finding id -> its supporting evidence ids (drives the finding→evidence highlight).
export type FindingEvidenceIndex = Readonly<Record<string, readonly string[]>>;

export interface WorkspaceViewModel extends DashboardViewModel {
  readonly evidence: readonly EvidenceViewModel[];
  readonly timeline: readonly TimelineEventViewModel[];
  readonly findingEvidence: FindingEvidenceIndex;
  // Entity ids referenced by the confirmed findings — the seeds the Graph Region
  // (ES-026) explores. Investigation-scoped because the backend Graph API is
  // entity-seeded (no investigation→graph endpoint).
  readonly seedEntities: readonly string[];
}

function toEvidenceViewModel(evidence: EvidenceDto): EvidenceViewModel {
  return {
    id: evidence.id,
    source: evidence.source,
    integrity: evidence.integrity,
    timestamp: evidence.timestamp,
    content: evidence.content,
  };
}

// Pure: a single chronological record of investigation activity derived from the
// evidence (`timestamp`) and finding (`created_at`) timestamps. There is no backend
// "event" source, so no business data is invented — only existing timestamps are
// reprojected. Events are ordered ascending by occurrence time.
export function deriveTimelineEvents(
  evidence: readonly EvidenceDto[],
  findings: readonly FindingDto[],
): readonly TimelineEventViewModel[] {
  const events: TimelineEventViewModel[] = [
    ...evidence.map((item) => ({
      id: `evidence:${item.id}`,
      kind: "evidence" as const,
      reference: item.id,
      label: item.source,
      occurredAt: item.timestamp,
    })),
    ...findings.map((finding) => ({
      id: `finding:${finding.id}`,
      kind: "finding" as const,
      reference: finding.id,
      label: finding.creator,
      occurredAt: finding.created_at,
    })),
  ];
  return events.sort(
    (a, b) => Date.parse(a.occurredAt) - Date.parse(b.occurredAt),
  );
}

// Pure: builds the finding→supporting-evidence lookup used to highlight the
// evidence that backs the currently selected finding.
export function buildFindingEvidenceIndex(
  findings: readonly FindingDto[],
): FindingEvidenceIndex {
  const index: Record<string, readonly string[]> = {};
  for (const finding of findings) {
    index[finding.id] = finding.supporting_evidence;
  }
  return index;
}

// Pure: the deduplicated entity ids referenced by the confirmed findings, in
// first-seen order. These are the Graph Region's exploration seeds — every seed is
// traceable to a presented finding.
export function collectSeedEntities(
  findings: readonly FindingDto[],
): readonly string[] {
  const seeds: string[] = [];
  const seen = new Set<string>();
  for (const finding of findings) {
    if (!isConfirmedFinding(finding.status)) {
      continue;
    }
    for (const entityId of finding.related_entities) {
      if (!seen.has(entityId)) {
        seen.add(entityId);
        seeds.push(entityId);
      }
    }
  }
  return seeds;
}

export function toWorkspaceViewModel(
  investigation: InvestigationDto,
  evidence: readonly EvidenceDto[],
  findings: readonly FindingDto[],
): WorkspaceViewModel {
  return {
    ...toDashboardViewModel(investigation, findings),
    evidence: evidence.map(toEvidenceViewModel),
    timeline: deriveTimelineEvents(evidence, findings),
    findingEvidence: buildFindingEvidenceIndex(findings),
    seedEntities: collectSeedEntities(findings),
  };
}

export async function loadInvestigationWorkspace(
  id: string,
  signal?: AbortSignal,
): Promise<WorkspaceViewModel> {
  const [investigation, evidence, findings] = await Promise.all([
    getInvestigation(id, signal),
    listEvidence(id, signal),
    listFindings(id, signal),
  ]);
  return toWorkspaceViewModel(investigation, evidence, findings);
}
