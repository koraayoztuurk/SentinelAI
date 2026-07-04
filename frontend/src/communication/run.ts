// Investigation run access + view model (ES-047).
//
// Triggers the backend's synchronous Investigation Loop run (ES-044) and maps
// its outcome summary. The DTO mirrors the backend response shape as a
// hand-written transitional copy (api-design §14a). A provider failure is
// never an HTTP error on this surface: it arrives as an `escalated` outcome
// carrying a stable failure code, which the UI presents rather than breaks on.

import { apiClient } from "./apiClient";

export interface RunActionResultDto {
  readonly action_id: string;
  readonly target: string | null;
  readonly execution_status: string;
  readonly error_code: string | null;
}

export interface RunOutcomeDto {
  readonly end: string;
  readonly cycles: number;
  readonly failure_code: string | null;
  readonly actions: readonly RunActionResultDto[];
}

export interface RunActionViewModel {
  readonly executionStatus: string;
  readonly target: string | null;
  readonly errorCode: string | null;
}

export interface RunOutcomeViewModel {
  readonly end: string;
  readonly cycles: number;
  readonly failureCode: string | null;
  readonly actions: readonly RunActionViewModel[];
}

export function toRunOutcomeViewModel(dto: RunOutcomeDto): RunOutcomeViewModel {
  return {
    end: dto.end,
    cycles: dto.cycles,
    failureCode: dto.failure_code,
    actions: dto.actions.map((action) => ({
      executionStatus: action.execution_status,
      target: action.target,
      errorCode: action.error_code,
    })),
  };
}

// The run is synchronous on the backend: each cycle may spend the provider's
// full execution bound, so this request gets a budget-sized timeout instead
// of the default one.
const RUN_TIMEOUT_MS = 120_000;

export async function runInvestigation(
  id: string,
): Promise<RunOutcomeViewModel> {
  const outcome = await apiClient.post<RunOutcomeDto>(
    `/api/v1/investigations/${encodeURIComponent(id)}/run`,
    undefined,
    { timeoutMs: RUN_TIMEOUT_MS },
  );
  return toRunOutcomeViewModel(outcome);
}
