// Memory region (ES-052).
//
// Replaces the "not yet available" placeholder: presents the organizational
// Memory Items originating from this investigation — the shared knowledge
// layer the AI retrieval reasons over (ES-051). The region never owns data:
// items come from the server-state layer (latest version per item) and
// refresh with the investigation family after a run.

import { useInvestigationMemory } from "../../state/useInvestigationMemory";
import { Button } from "../../ui/Button";
import { WorkspaceRegion } from "./WorkspaceRegion";

export interface MemorySectionProps {
  readonly investigationId: string;
}

const STATUS_STYLES: Record<string, string> = {
  candidate: "border-info/50 text-info",
  verified: "border-ok/50 text-ok",
  deprecated: "border-line-strong text-faint",
};

export function MemorySection({ investigationId }: MemorySectionProps) {
  const memory = useInvestigationMemory(investigationId);

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
              <p className="mono-label mt-1 tabular-nums text-faint">
                v{item.version} · confidence {Math.round(item.confidence * 100)}%
              </p>
            </li>
          ))}
        </ul>
      )}
    </WorkspaceRegion>
  );
}
