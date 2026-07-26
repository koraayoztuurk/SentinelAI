// Memory region (ES-052).
//
// Replaces the "not yet available" placeholder: presents the organizational
// Memory Items originating from this investigation — the shared knowledge
// layer the AI retrieval reasons over (ES-051). The region never owns data:
// items come from the server-state layer (latest version per item) and
// refresh with the investigation family after a run.

import { useState } from "react";
import { useEraseMemoryItem } from "../../state/useEraseMemoryItem";
import { useInvestigationMemory } from "../../state/useInvestigationMemory";
import { usePlatformStatus } from "../../state/usePlatformStatus";
import { Button } from "../../ui/Button";
import { WorkspaceRegion } from "./WorkspaceRegion";

export interface MemorySectionProps {
  readonly investigationId: string;
}

// The capability that authorizes destroying organizational knowledge
// (ADR-019). Shared knowledge is readable by anyone authenticated and
// erasable only by someone granted this.
const ERASE_KNOWLEDGE_CAPABILITY = "knowledge:erase";

const STATUS_STYLES: Record<string, string> = {
  candidate: "border-info/50 text-info",
  verified: "border-ok/50 text-ok",
  deprecated: "border-line-strong text-faint",
  erased: "border-danger/50 text-danger",
};

export function MemorySection({ investigationId }: MemorySectionProps) {
  const memory = useInvestigationMemory(investigationId);
  const platform = usePlatformStatus();
  const erasure = useEraseMemoryItem(investigationId);
  const [pendingErase, setPendingErase] = useState<string | null>(null);
  // The control is offered only to an identity that may actually use it
  // (ADR-019). This is presentation courtesy, not enforcement — the backend
  // refuses regardless, and must, since a client cannot be trusted.
  const mayErase =
    platform.status?.capabilities.includes(ERASE_KNOWLEDGE_CAPABILITY) ?? false;

  return (
    <WorkspaceRegion title="Memory">
      {memory.error && (
        <p role="alert" className="text-xs text-danger">
          Could not load memory ({memory.error.code}).
          <Button className="btn-link ml-2 text-xs" onClick={memory.retry}>
            Retry
          </Button>
        </p>
      )}

      {memory.loading && (
        <div role="status" className="grid gap-2">
          <span className="sr-only">Loading memory…</span>
          <div className="shimmer h-10 w-full" aria-hidden="true" />
          <div className="shimmer h-10 w-3/4" aria-hidden="true" />
        </div>
      )}

      {!memory.loading && !memory.error && memory.items.length === 0 && (
        <p className="text-sm text-faint">
          No memory items yet. Knowledge promoted from this investigation will
          appear here.
        </p>
      )}

      {memory.items.length > 0 && (
        <ul className="stagger grid max-h-72 gap-2 overflow-y-auto text-sm">
          {memory.items.map((item) => (
            <li key={item.id} className="card px-3 py-2">
              <div className="flex items-center justify-between gap-2">
                <span className="mono-label uppercase text-muted">
                  {item.type}
                </span>
                <span
                  className={`mono-label rounded-full border bg-panel-2/60 px-2 py-0.5 ${
                    STATUS_STYLES[item.status] ?? "border-line-strong"
                  }`}
                >
                  {item.status}
                </span>
              </div>
              {item.content !== "" && <p className="mt-1">{item.content}</p>}
              <div className="mt-1 flex items-end justify-between gap-2">
                <p className="mono-label tabular-nums text-faint">
                  v{item.version} · confidence{" "}
                  {Math.round(item.confidence * 100)}%
                </p>
                {mayErase && item.status !== "erased" && (
                  pendingErase === item.id ? (
                    <span className="flex items-center gap-2">
                      <span className="mono-label text-danger">
                        Erase permanently?
                      </span>
                      <Button
                        className="btn btn-primary bg-danger/80 text-xs hover:bg-danger"
                        onClick={() => {
                          erasure.erase(item.id);
                          setPendingErase(null);
                        }}
                        disabled={erasure.erasingId === item.id}
                      >
                        Confirm
                      </Button>
                      <Button
                        className="btn btn-ghost text-xs"
                        onClick={() => setPendingErase(null)}
                      >
                        Cancel
                      </Button>
                    </span>
                  ) : (
                    <Button
                      className="btn btn-ghost text-xs text-danger"
                      onClick={() => setPendingErase(item.id)}
                    >
                      Erase
                    </Button>
                  )
                )}
              </div>
            </li>
          ))}
        </ul>
      )}

      {erasure.error && (
        <p role="alert" className="mt-2 text-xs text-danger">
          Could not erase the memory item ({erasure.error.code}).
        </p>
      )}
    </WorkspaceRegion>
  );
}
