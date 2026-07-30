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

const READINESS_TONE: Record<string, string> = {
  ready: "text-mint-ink",
  degraded: "text-amber-ink",
  not_ready: "text-coral-ink",
};

const CIRCUIT_TONE: Record<string, string> = {
  closed: "text-mint-ink",
  half_open: "text-amber-ink",
  open: "text-coral-ink",
};

function storeTone(state: string, gating: boolean): string {
  if (state === "ok") return "text-mint-ink";
  // A degradable store being unavailable is a reduced capability, not an
  // outage — showing both in the same red would erase the distinction the
  // backend deliberately makes.
  return gating ? "text-coral-ink" : "text-amber-ink";
}

function Block({
  title,
  children,
}: {
  readonly title: string;
  readonly children: React.ReactNode;
}) {
  return (
    <div className="rounded-input bg-paper-2 p-3.5">
      <h3 className="mono-label uppercase text-ink-3">{title}</h3>
      <div className="mt-2">{children}</div>
    </div>
  );
}

export function PlatformSection() {
  const platform = usePlatformStatus();
  const status = platform.status;

  return (
    <WorkspaceRegion
      title="Platform"
      note="The health of the tool itself — its stores, its AI providers, how it handles data at end of life, and whether its audit record is tamper-evident."
      action={
        status && (
          <span
            className={`text-sm font-bold ${
              READINESS_TONE[status.readiness] ?? "text-ink-2"
            }`}
          >
            {status.readiness}
          </span>
        )
      }
    >
      {platform.error && (
        <p
          role="alert"
          className="rounded-input border border-coral/50 bg-coral/10 px-3 py-2 text-xs text-coral-ink"
        >
          Could not load platform status ({platform.error.code}).
          <Button variant="link" className="ml-2" onClick={platform.retry}>
            Retry
          </Button>
        </p>
      )}

      {platform.loading && (
        <div role="status" className="grid gap-2">
          <span className="sr-only">Loading platform status…</span>
          <div className="skeleton h-16 w-full" aria-hidden="true" />
          <div className="skeleton h-16 w-2/3" aria-hidden="true" />
        </div>
      )}

      {status && (
        <div className="grid gap-3">
          <p className="mono-label uppercase text-ink-3">
            {status.environment} · v{status.version}
          </p>

          <div className="grid gap-3 sm:grid-cols-2">
            <Block title="Stores">
              <ul className="grid gap-1.5 text-sm">
                {status.stores.map((store) => (
                  <li
                    key={store.name}
                    className="flex items-center justify-between gap-2"
                  >
                    <span className="text-ink-2">
                      {store.name}
                      {!store.gating && (
                        <span className="mono-label ml-2 text-ink-3">
                          degradable
                        </span>
                      )}
                    </span>
                    <span
                      className={`mono-label font-semibold ${storeTone(store.state, store.gating)}`}
                    >
                      {store.state}
                    </span>
                  </li>
                ))}
              </ul>
            </Block>

            <Block title="Resilience">
              {status.providers.length === 0 ? (
                <p className="text-xs leading-relaxed text-ink-3">
                  No provider calls yet — a circuit only has a state once it has
                  been used.
                </p>
              ) : (
                <ul className="grid gap-1.5 text-sm">
                  {status.providers.map((provider) => (
                    <li
                      key={provider.name}
                      className="flex items-center justify-between gap-2"
                    >
                      <span className="text-ink-2">{provider.name}</span>
                      <span
                        className={`mono-label font-semibold ${
                          CIRCUIT_TONE[provider.circuit] ?? "text-ink-3"
                        }`}
                      >
                        {provider.circuit}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
              <p className="mono-label mt-2 tabular-nums text-ink-3">
                {status.llmFallbacks} failovers · {status.deadLetters}{" "}
                dead-lettered · {status.deferredErasures} erasures deferred
              </p>
            </Block>

            <Block title="Data lifecycle">
              <p className="text-sm leading-relaxed text-ink-2">
                {status.retentionEnforced ? (
                  <>
                    Investigations are erased automatically after{" "}
                    <span className="tabular-nums font-semibold text-ink">
                      {status.retentionDays}
                    </span>{" "}
                    days.
                  </>
                ) : (
                  <>
                    Automatic retention is <strong>not enforced</strong>. Erasure
                    happens on request only.
                  </>
                )}
              </p>
              <p className="mono-label mt-2 tabular-nums text-ink-3">
                {status.investigationsErased} erased by policy ·{" "}
                {status.retentionFailures} failed · payloads{" "}
                {status.payloadErasureStrategy === "crypto_shred"
                  ? "crypto-shredded"
                  : "deleted"}
              </p>
            </Block>

            <Block title="Audit">
              <p className="text-sm leading-relaxed text-ink-2">
                {status.auditDurable ? (
                  <>
                    Actions are recorded in the durable, tamper-evident audit log
                    and kept for{" "}
                    <span className="tabular-nums font-semibold text-ink">
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
                <p role="alert" className="mono-label mt-2 text-coral-ink">
                  {status.auditWriteFailures} audit records could not be stored.
                </p>
              )}
            </Block>
          </div>
        </div>
      )}
    </WorkspaceRegion>
  );
}
