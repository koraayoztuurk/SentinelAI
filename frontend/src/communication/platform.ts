// Platform status data access + view model (ES-070).
//
// The operational posture of the backend: store readiness, provider and
// projection health, the data-lifecycle policy this deployment configured, the
// audit sink, and the caller's own capabilities. The DTO mirrors the backend
// response as a hand-written transitional copy (api-design §14a); the UI
// consumes the mapped view model only.
//
// Presented, never owned: every value here describes the backend's condition,
// so the frontend renders what it is told and derives no operational judgement
// of its own beyond how to display it.

import { apiClient } from "./apiClient";

export interface PlatformStatusDto {
  readonly environment: string;
  readonly version: string;
  readonly readiness: {
    readonly status: string;
    readonly postgres: string;
    readonly neo4j: string;
    readonly qdrant: string;
    readonly gating: readonly string[];
  };
  readonly resilience: {
    readonly providers: readonly {
      readonly provider: string;
      readonly circuit: string;
    }[];
    readonly llm_fallbacks: number;
    readonly projection_dead_letters: Record<string, number>;
    readonly payload_erasures_deferred: number;
  };
  readonly data_lifecycle: {
    readonly retention_days: number;
    readonly retention_enforced: boolean;
    readonly investigations_erased: number;
    readonly retention_failures: number;
    readonly payload_erasure_strategy: string;
    readonly audit_retention_days: number;
  };
  readonly audit: {
    readonly sink: string;
    readonly durable: boolean;
    readonly write_failures: number;
  };
  readonly capabilities: readonly string[];
}

export interface StoreStatusViewModel {
  readonly name: string;
  readonly state: string;
  readonly gating: boolean;
}

export interface PlatformStatusViewModel {
  readonly environment: string;
  readonly version: string;
  readonly readiness: string;
  readonly stores: readonly StoreStatusViewModel[];
  readonly providers: readonly { readonly name: string; readonly circuit: string }[];
  readonly llmFallbacks: number;
  readonly deadLetters: number;
  readonly deferredErasures: number;
  readonly retentionDays: number;
  readonly retentionEnforced: boolean;
  readonly investigationsErased: number;
  readonly retentionFailures: number;
  readonly payloadErasureStrategy: string;
  readonly auditRetentionDays: number;
  readonly auditSink: string;
  readonly auditDurable: boolean;
  readonly auditWriteFailures: number;
  readonly capabilities: readonly string[];
}

export function toPlatformStatusViewModel(
  dto: PlatformStatusDto,
): PlatformStatusViewModel {
  const gating = new Set(dto.readiness.gating);
  return {
    environment: dto.environment,
    version: dto.version,
    readiness: dto.readiness.status,
    stores: (["postgres", "neo4j", "qdrant"] as const).map((name) => ({
      name,
      state: dto.readiness[name],
      gating: gating.has(name),
    })),
    providers: dto.resilience.providers.map((provider) => ({
      name: provider.provider,
      circuit: provider.circuit,
    })),
    llmFallbacks: dto.resilience.llm_fallbacks,
    // One number is what an operator acts on: any projection stuck is the
    // same signal regardless of which one it was.
    deadLetters: Object.values(dto.resilience.projection_dead_letters).reduce(
      (total, count) => total + count,
      0,
    ),
    deferredErasures: dto.resilience.payload_erasures_deferred,
    retentionDays: dto.data_lifecycle.retention_days,
    retentionEnforced: dto.data_lifecycle.retention_enforced,
    investigationsErased: dto.data_lifecycle.investigations_erased,
    retentionFailures: dto.data_lifecycle.retention_failures,
    payloadErasureStrategy: dto.data_lifecycle.payload_erasure_strategy,
    auditRetentionDays: dto.data_lifecycle.audit_retention_days,
    auditSink: dto.audit.sink,
    auditDurable: dto.audit.durable,
    auditWriteFailures: dto.audit.write_failures,
    capabilities: dto.capabilities,
  };
}

export async function loadPlatformStatus(
  signal?: AbortSignal,
): Promise<PlatformStatusViewModel> {
  const status = await apiClient.get<PlatformStatusDto>(
    "/api/v1/platform/status",
    { signal },
  );
  return toPlatformStatusViewModel(status);
}
