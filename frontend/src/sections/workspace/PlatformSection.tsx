// Platform region (ES-070) — the operational surface of Milestone G.
//
// Every hardening the milestone delivered works silently: a breaker that never
// opens, a projection that never dead-letters, an audit chain nobody reads, a
// retention sweep that erases on its own. Silent is exactly the problem — an
// operator cannot confirm a guarantee they cannot see. This region makes the
// posture legible in one place.
//
// It presents, never judges: the backend decides what is ready, degraded or
// enforced; the region renders that verdict and adds no opinion of its own.

import { usePlatformStatus } from "../../state/usePlatformStatus";
import { Button } from "../../ui/Button";
import { WorkspaceRegion } from "./WorkspaceRegion";

const READINESS_STYLES: Record<string, string> = {
  ready: "border-ok/50 text-ok",
  degraded: "border-warn/50 text-warn",
  not_ready: "border-danger/50 text-danger",
};

const CIRCUIT_STYLES: Record<string, string> = {
  closed: "text-ok",
  half_open: "text-warn",
  open: "text-danger",
};

function storeStyle(state: string, gating: boolean): string {
  if (state === "ok") return "text-ok";
  // A degradable store being unavailable is a reduced capability, not an
  // outage — showing both in the same red would erase the distinction the
  // backend deliberately makes.
  return gating ? "text-danger" : "text-warn";
}

export function PlatformSection() {
  const platform = usePlatformStatus();
  const status = platform.status;

  return (
    <WorkspaceRegion title="Platform">
      {platform.error && (
        <p role="alert" className="text-xs text-danger">
          Could not load platform status ({platform.error.code}).
          <Button className="btn-link ml-2 text-xs" onClick={platform.retry}>
            Retry
          </Button>
        </p>
      )}

      {platform.loading && (
        <div role="status" className="grid gap-2">
          <span className="sr-only">Loading platform status…</span>
          <div className="shimmer h-10 w-full" aria-hidden="true" />
          <div className="shimmer h-10 w-2/3" aria-hidden="true" />
        </div>
      )}

      {status && (
        <div className="grid gap-3 text-sm">
          <div className="flex items-center justify-between gap-2">
            <span className="mono-label uppercase text-muted">
              {status.environment} · v{status.version}
            </span>
            <span
              className={`mono-label rounded-full border bg-panel-2/60 px-2 py-0.5 ${
                READINESS_STYLES[status.readiness] ?? "border-line-strong"
              }`}
            >
              {status.readiness}
            </span>
          </div>

          <div>
            <h4 className="mono-label uppercase text-faint">Stores</h4>
            <ul className="mt-1 grid gap-1">
              {status.stores.map((store) => (
                <li
                  key={store.name}
                  className="flex items-center justify-between gap-2"
                >
                  <span className="text-muted">
                    {store.name}
                    {!store.gating && (
                      <span className="mono-label ml-2 text-faint">
                        degradable
                      </span>
                    )}
                  </span>
                  <span className={storeStyle(store.state, store.gating)}>
                    {store.state}
                  </span>
                </li>
              ))}
            </ul>
          </div>

          <div>
            <h4 className="mono-label uppercase text-faint">Resilience</h4>
            {status.providers.length === 0 ? (
              <p className="mt-1 text-xs text-faint">
                No provider calls yet — a circuit only has a state once it has
                been used.
              </p>
            ) : (
              <ul className="mt-1 grid gap-1">
                {status.providers.map((provider) => (
                  <li
                    key={provider.name}
                    className="flex items-center justify-between gap-2"
                  >
                    <span className="text-muted">{provider.name}</span>
                    <span
                      className={CIRCUIT_STYLES[provider.circuit] ?? "text-faint"}
                    >
                      {provider.circuit}
                    </span>
                  </li>
                ))}
              </ul>
            )}
            <p className="mono-label mt-1 tabular-nums text-faint">
              {status.llmFallbacks} failovers · {status.deadLetters}{" "}
              dead-lettered · {status.deferredErasures} erasures deferred
            </p>
          </div>

          <div>
            <h4 className="mono-label uppercase text-faint">Data lifecycle</h4>
            <p className="mt-1 text-muted">
              {status.retentionEnforced ? (
                <>
                  Investigations are erased automatically after{" "}
                  <span className="tabular-nums">{status.retentionDays}</span>{" "}
                  days.
                </>
              ) : (
                <>
                  Automatic retention is <strong>not enforced</strong>. Erasure
                  happens on request only.
                </>
              )}
            </p>
            <p className="mono-label mt-1 tabular-nums text-faint">
              {status.investigationsErased} erased by policy ·{" "}
              {status.retentionFailures} failed · payloads{" "}
              {status.payloadErasureStrategy === "crypto_shred"
                ? "crypto-shredded"
                : "deleted"}
            </p>
          </div>

          <div>
            <h4 className="mono-label uppercase text-faint">Audit</h4>
            <p className="mt-1 text-muted">
              {status.auditDurable ? (
                <>
                  Actions are recorded in the durable, tamper-evident audit log
                  and kept for{" "}
                  <span className="tabular-nums">
                    {status.auditRetentionDays}
                  </span>{" "}
                  days.
                </>
              ) : (
                <>
                  The audit sink is <strong>log-only</strong>: records are not
                  durable or tamper-evident.
                </>
              )}
            </p>
            {status.auditWriteFailures > 0 && (
              <p role="alert" className="mono-label mt-1 text-danger">
                {status.auditWriteFailures} audit records could not be stored.
              </p>
            )}
          </div>
        </div>
      )}
    </WorkspaceRegion>
  );
}
