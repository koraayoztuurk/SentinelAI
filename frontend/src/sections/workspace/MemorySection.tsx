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
  candidate: "border-sky-500/50 text-sky-400",
  verified: "border-emerald-500/50 text-emerald-400",
  deprecated: "border-white/20 opacity-60",
};

export function MemorySection({ investigationId }: MemorySectionProps) {
  const memory = useInvestigationMemory(investigationId);

  return (
    <WorkspaceRegion title="Memory">
      {memory.error && (
        <p role="alert" className="text-xs text-red-400">
          Could not load memory ({memory.error.code}).
          <Button className="ml-2 underline" onClick={memory.retry}>
            Retry
          </Button>
        </p>
      )}

      {memory.loading && (
        <p role="status" className="text-sm opacity-50">
          Loading memory…
        </p>
      )}

      {!memory.loading && !memory.error && memory.items.length === 0 && (
        <p className="text-sm opacity-50">
          No memory items yet. Knowledge promoted from this investigation will
          appear here.
        </p>
      )}

      {memory.items.length > 0 && (
        <ul className="grid max-h-72 gap-2 overflow-y-auto text-sm">
          {memory.items.map((item) => (
            <li
              key={item.id}
              className="rounded border border-white/10 px-3 py-2"
            >
              <div className="flex items-center justify-between gap-2">
                <span className="font-mono text-xs uppercase opacity-70">
                  {item.type}
                </span>
                <span
                  className={`rounded border px-2 py-0.5 text-xs ${
                    STATUS_STYLES[item.status] ?? "border-white/20"
                  }`}
                >
                  {item.status}
                </span>
              </div>
              {item.content !== "" && <p className="mt-1">{item.content}</p>}
              <p className="mt-1 text-xs opacity-50">
                v{item.version} · confidence {Math.round(item.confidence * 100)}%
              </p>
            </li>
          ))}
        </ul>
      )}
    </WorkspaceRegion>
  );
}
