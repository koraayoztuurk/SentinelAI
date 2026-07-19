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
  // Organization access scope (ES-063, ADR-016) — server-derived.
  readonly tenant: string;
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
  readonly priority: string;
  // `owner` is intentionally absent (ES-062): the backend derives the owner
  // from the authenticated subject — the creator owns what they create.
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

// Evidence payload store (ES-060/061): raw bytes up (returns the content
// address the evidence record carries as its integrity value) and verified
// bytes down. Payloads travel as octet-streams, never JSON (api-design §8).
export interface EvidencePayloadStoredDto {
  readonly address: string;
  readonly size_bytes: number;
}

export function uploadEvidencePayload(
  investigationId: string,
  bytes: ArrayBuffer,
): Promise<EvidencePayloadStoredDto> {
  return apiClient.postBinary<EvidencePayloadStoredDto>(
    `/api/v1/investigations/${encodeURIComponent(investigationId)}/evidence/payloads`,
    bytes,
  );
}

export function downloadEvidencePayload(
  investigationId: string,
  evidenceId: string,
): Promise<Blob> {
  return apiClient.getBlob(
    `/api/v1/investigations/${encodeURIComponent(investigationId)}` +
      `/evidence/${encodeURIComponent(evidenceId)}/payload`,
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
