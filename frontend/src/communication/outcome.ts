// Investigation Outcome data access + view model (ES-055).
//
// Read-only access to the synthesized Investigation Outcome (ES-045 read
// surface; the Decision Engine is its writer). An investigation has at most
// one outcome — a missing outcome is a normal state (`null`), not an error.
// The DTO mirrors the backend response shape as a hand-written transitional
// copy (api-design §14a); the UI consumes the mapped view model only.

import { apiClient } from "./apiClient";
import { ApiError } from "./errors";

export interface OutcomeDto {
  readonly id: string;
  readonly investigation_id: string;
  readonly confidence: number;
  readonly recommendation: string;
  readonly status: string;
  readonly created_at: string;
  readonly contributing_findings: readonly string[];
  readonly detected_conflicts: readonly string[];
  readonly open_questions: readonly string[];
  readonly report_id: string | null;
}

export interface OutcomeViewModel {
  readonly id: string;
  readonly status: string;
  readonly confidence: number;
  readonly recommendation: string;
  readonly contributingFindings: readonly string[];
  readonly detectedConflicts: readonly string[];
  readonly openQuestions: readonly string[];
  readonly createdAt: string;
}

export function toOutcomeViewModel(dto: OutcomeDto): OutcomeViewModel {
  return {
    id: dto.id,
    status: dto.status,
    confidence: dto.confidence,
    recommendation: dto.recommendation,
    contributingFindings: dto.contributing_findings,
    detectedConflicts: dto.detected_conflicts,
    openQuestions: dto.open_questions,
    createdAt: dto.created_at,
  };
}

export async function loadInvestigationOutcome(
  id: string,
  signal?: AbortSignal,
): Promise<OutcomeViewModel | null> {
  try {
    const dto = await apiClient.get<OutcomeDto>(
      `/api/v1/investigations/${encodeURIComponent(id)}/outcome`,
      { signal },
    );
    return toOutcomeViewModel(dto);
  } catch (error) {
    // 0..1 semantics: "no outcome yet" is a normal state, not a failure.
    if (
      error instanceof ApiError &&
      error.code === "investigation.outcome_not_found"
    ) {
      return null;
    }
    throw error;
  }
}
