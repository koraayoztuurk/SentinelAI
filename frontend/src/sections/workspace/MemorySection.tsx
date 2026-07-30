// Memory region (ES-052).
//
// Presents the organizational Memory Items originating from this investigation
// — the shared knowledge layer the AI retrieval reasons over (ES-051). The
// region never owns data: items come from the server-state layer (latest
// version per item) and refresh with the investigation family after a run.

import { useState } from "react";
import type { ConfirmedFindingViewModel } from "../../communication/dashboard";
import { useEraseMemoryItem } from "../../state/useEraseMemoryItem";
import { useInvestigationMemory } from "../../state/useInvestigationMemory";
import { usePlatformStatus } from "../../state/usePlatformStatus";
import { usePromoteMemory } from "../../state/usePromoteMemory";
import { StatusBadge } from "../../components/dashboard/StatusBadge";
import { Button } from "../../ui/Button";
import { Disclosure } from "../../ui/Disclosure";
import { Empty } from "../../ui/Region";
import { WorkspaceRegion } from "./WorkspaceRegion";

export interface MemorySectionProps {
  readonly investigationId: string;
  /** Confirmed findings a promotion can cite; optional so the region stays
      usable (read-only) wherever findings are not to hand. */
  readonly findings?: readonly ConfirmedFindingViewModel[];
}

// The vocabulary is an open string in the domain; these are the kinds this
// investigation surface offers, not a closed set the platform enforces.
const MEMORY_TYPES = [
  "attack_pattern",
  "ioc",
  "mitigation",
  "analyst_note",
] as const;

function PromoteForm({
  investigationId,
  findings,
}: {
  readonly investigationId: string;
  readonly findings: readonly ConfirmedFindingViewModel[];
}) {
  const [content, setContent] = useState("");
  const [type, setType] = useState<string>(MEMORY_TYPES[0]);
  const [confidence, setConfidence] = useState(80);
  const [cited, setCited] = useState<readonly string[]>([]);
  const { promote, promoting, error } = usePromoteMemory(investigationId);

  const submit = () => {
    if (content.trim().length === 0) {
      return;
    }
    promote({
      type,
      source_investigation_id: investigationId,
      confidence: confidence / 100,
      status: "verified",
      content: content.trim(),
      referenced_findings: cited,
    });
    setContent("");
    setCited([]);
  };

  return (
    <div className="grid gap-3">
      <p className="text-xs leading-relaxed text-ink-2">
        Write what a colleague should know next time, not what happened here.
        Promoted knowledge outlives this case and is what future investigations
        are searched against.
      </p>

      <textarea
        aria-label="Knowledge to remember"
        placeholder="e.g. This actor fronts its C2 with a disposable CDN domain and rotates it weekly — blocking the resolved IP alone is not enough."
        value={content}
        rows={3}
        className="input resize-y"
        onChange={(event) => setContent(event.target.value)}
      />

      <div className="flex flex-wrap items-center gap-x-4 gap-y-3">
        <label className="flex items-center gap-2 text-[0.8125rem] text-ink-2">
          Kind
          <select
            aria-label="Knowledge kind"
            value={type}
            className="input py-2"
            onChange={(event) => setType(event.target.value)}
          >
            {MEMORY_TYPES.map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
        </label>
        <label className="flex items-center gap-2.5 text-[0.8125rem] text-ink-2">
          Confidence
          <input
            type="range"
            min={0}
            max={100}
            step={5}
            value={confidence}
            aria-label="Knowledge confidence"
            className="w-32 accent-[var(--color-lav)]"
            onChange={(event) => setConfidence(Number(event.target.value))}
          />
          <span className="mono-label w-9 tabular-nums font-semibold text-ink">
            {confidence}%
          </span>
        </label>
      </div>

      {findings.length > 0 && (
        <fieldset className="grid gap-1">
          <legend className="mono-label uppercase text-ink-3">
            Came from (optional)
          </legend>
          {findings.map((finding) => (
            <label
              key={finding.id}
              className="flex cursor-pointer items-center gap-2.5 rounded-input px-2.5 py-1.5 hover:bg-paper-2"
            >
              <input
                type="checkbox"
                checked={cited.includes(finding.id)}
                onChange={() =>
                  setCited((current) =>
                    current.includes(finding.id)
                      ? current.filter((value) => value !== finding.id)
                      : [...current, finding.id],
                  )
                }
                className="h-4 w-4 shrink-0 accent-[var(--color-lav)]"
              />
              <span className="mono-label truncate text-ink-2">
                {finding.id}
              </span>
            </label>
          ))}
        </fieldset>
      )}

      <div>
        <Button
          variant="soft"
          onClick={submit}
          busy={promoting}
          disabled={content.trim().length === 0}
        >
          {promoting ? "Promoting…" : "Promote to memory"}
        </Button>
      </div>

      {error && (
        <p
          role="alert"
          className="rounded-input border border-coral/50 bg-coral/10 px-3 py-2 text-xs text-coral-ink"
        >
          Could not promote the knowledge ({error.code}).
        </p>
      )}
    </div>
  );
}

// The capability that authorizes destroying organizational knowledge
// (ADR-019). Shared knowledge is readable by anyone authenticated and
// erasable only by someone granted this.
const ERASE_KNOWLEDGE_CAPABILITY = "knowledge:erase";

export function MemorySection({
  investigationId,
  findings = [],
}: MemorySectionProps) {
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
    <WorkspaceRegion
      title="Memory"
      note="What this investigation taught the organisation. These items outlive the case and are what future investigations get searched against."
    >
      {memory.error && (
        <p
          role="alert"
          className="rounded-input border border-coral/50 bg-coral/10 px-3 py-2 text-xs text-coral-ink"
        >
          Could not load memory ({memory.error.code}).
          <Button variant="link" className="ml-2" onClick={memory.retry}>
            Retry
          </Button>
        </p>
      )}

      {memory.loading && (
        <div role="status" className="grid gap-2">
          <span className="sr-only">Loading memory…</span>
          <div className="skeleton h-14 w-full" aria-hidden="true" />
          <div className="skeleton h-14 w-3/4" aria-hidden="true" />
        </div>
      )}

      {!memory.loading && !memory.error && memory.items.length === 0 && (
        <Empty>
          No memory items yet. Knowledge confirmed here becomes searchable for
          every future investigation.
        </Empty>
      )}

      {memory.items.length > 0 && (
        <ul className="grid max-h-[24rem] gap-2 overflow-y-auto pr-1">
          {memory.items.map((item) => (
            <li key={item.id} className="card p-3.5">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="mono-label uppercase text-ink-2">
                  {item.type}
                </span>
                <StatusBadge status={item.status} />
              </div>
              {item.content !== "" && (
                <p className="mt-2 text-sm leading-relaxed">{item.content}</p>
              )}
              <div className="mt-2.5 flex flex-wrap items-center justify-between gap-2">
                <p className="mono-label tabular-nums text-ink-3">
                  v{item.version} · confidence{" "}
                  {Math.round(item.confidence * 100)}%
                </p>
                {mayErase &&
                  item.status !== "erased" &&
                  (pendingErase === item.id ? (
                    <span className="flex flex-wrap items-center gap-2">
                      <span className="mono-label font-semibold text-coral-ink">
                        Erase permanently?
                      </span>
                      <Button
                        variant="danger"
                        className="btn-sm"
                        onClick={() => {
                          erasure.erase(item.id);
                          setPendingErase(null);
                        }}
                        busy={erasure.erasingId === item.id}
                      >
                        Confirm
                      </Button>
                      <Button
                        variant="outline"
                        className="btn-sm"
                        onClick={() => setPendingErase(null)}
                      >
                        Cancel
                      </Button>
                    </span>
                  ) : (
                    <Button
                      variant="outline"
                      className="btn-sm text-coral-ink"
                      onClick={() => setPendingErase(item.id)}
                    >
                      Erase
                    </Button>
                  ))}
              </div>
            </li>
          ))}
        </ul>
      )}

      {erasure.error && (
        <p
          role="alert"
          className="mt-3 rounded-input border border-coral/50 bg-coral/10 px-3 py-2 text-xs text-coral-ink"
        >
          Could not erase the memory item ({erasure.error.code}).
        </p>
      )}

      <div className="mt-5 border-t border-line pt-4">
        <Disclosure
          summary="Promote knowledge from this investigation"
          defaultOpen={!memory.loading && memory.items.length === 0}
        >
          <PromoteForm
            investigationId={investigationId}
            findings={findings}
          />
        </Disclosure>
      </div>
    </WorkspaceRegion>
  );
}
