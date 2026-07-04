// Investigation data access.
//
// Typed access to the backend Investigation API through the shared `apiClient`
// (the single Backend API boundary). The DTOs mirror the backend response shapes
// (ES-015); they stay internal to the communication layer — the UI consumes view
// models, not these DTOs. Every call forwards an optional `AbortSignal` so request
// cancellation reaches the communication layer.

import { apiClient } from "./apiClient";

export interface InvestigationDto {
  readonly id: string;
  readonly title: string;
  readonly status: string;
  readonly created_at: string;
  readonly owner: string;
  readonly priority: string;
}

export interface FindingDto {
  readonly id: string;
  readonly investigation_id: string;
  readonly supporting_evidence: readonly string[];
  readonly creator: string;
  readonly created_at: string;
  readonly confidence: number;
  readonly status: string;
  readonly related_entities: readonly string[];
  readonly related_relationships: readonly string[];
}

export interface EvidenceDto {
  readonly id: string;
  readonly investigation_id: string;
  readonly source: string;
  readonly timestamp: string;
  readonly integrity: string;
  readonly content: string;
}

export interface InvestigationCreateInput {
  readonly title: string;
  readonly owner: string;
  readonly priority: string;
}

export function createInvestigation(
  input: InvestigationCreateInput,
): Promise<InvestigationDto> {
  return apiClient.post<InvestigationDto>("/api/v1/investigations", input);
}

export interface EvidenceCreateInput {
  readonly source: string;
  readonly integrity: string;
  readonly content: string;
}

export function attachEvidence(
  investigationId: string,
  input: EvidenceCreateInput,
): Promise<EvidenceDto> {
  return apiClient.post<EvidenceDto>(
    `/api/v1/investigations/${encodeURIComponent(investigationId)}/evidence`,
    input,
  );
}

export function getInvestigation(
  id: string,
  signal?: AbortSignal,
): Promise<InvestigationDto> {
  return apiClient.get<InvestigationDto>(
    `/api/v1/investigations/${encodeURIComponent(id)}`,
    { signal },
  );
}

export function listFindings(
  id: string,
  signal?: AbortSignal,
): Promise<readonly FindingDto[]> {
  return apiClient.get<readonly FindingDto[]>(
    `/api/v1/investigations/${encodeURIComponent(id)}/findings`,
    { signal },
  );
}

export function listEvidence(
  id: string,
  signal?: AbortSignal,
): Promise<readonly EvidenceDto[]> {
  return apiClient.get<readonly EvidenceDto[]>(
    `/api/v1/investigations/${encodeURIComponent(id)}/evidence`,
    { signal },
  );
}
