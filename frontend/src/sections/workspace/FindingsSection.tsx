// Findings region (investigation-workspace §5).
//
// Presents the confirmed (validated/accepted) findings — reused from the shared view
// model — while preserving traceability: selecting a finding drives the
// finding→evidence highlight in the Evidence Region through the shared Investigation
// Context.
//
// The region also lets the analyst record a finding, which the workspace
// previously could not do at all: findings were reachable only through the REST
// API, so the platform's own loop (evidence → finding → run → recommendation)
// could not be completed from the browser, and the Decision Engine — which
// synthesizes only from *confirmed* findings — had nothing to work with.
//
// A finding recorded here is `validated`: the analyst weighed the evidence and
// is recording the conclusion (domain-model §6 — findings are produced by agents
// *or* analysts). `proposed` belongs to findings produced *for* review. Domain
// Rule 2 (a finding requires supporting evidence) is enforced by the service and
// mirrored here, so the control is unavailable rather than failing on submit.

import { useState } from "react";
import type { ConfirmedFindingViewModel } from "../../communication/dashboard";
import type { EvidenceViewModel } from "../../communication/workspace";
import { getDevAuthSubject } from "../../state/devAuth";
import { useRecordFinding } from "../../state/useRecordFinding";
import { useWorkspaceContext } from "../../state/workspaceContext";
import { WorkspaceFindingCard } from "../../components/workspace/WorkspaceFindingCard";
import { Button } from "../../ui/Button";
import { Disclosure } from "../../ui/Disclosure";
import { Empty } from "../../ui/Region";
import { WorkspaceRegion } from "./WorkspaceRegion";

export interface FindingsSectionProps {
  readonly findings: readonly ConfirmedFindingViewModel[];
  readonly investigationId: string;
  readonly evidence: readonly EvidenceViewModel[];
}

function RecordFindingForm({
  investigationId,
  evidence,
}: {
  readonly investigationId: string;
  readonly evidence: readonly EvidenceViewModel[];
}) {
  const [selected, setSelected] = useState<readonly string[]>([]);
  const [confidence, setConfidence] = useState(80);
  const [entities, setEntities] = useState("");
  const { record, recording, error } = useRecordFinding(investigationId);
  const creator = getDevAuthSubject();

  const toggle = (id: string) =>
    setSelected((current) =>
      current.includes(id)
        ? current.filter((value) => value !== id)
        : [...current, id],
    );

  const submit = () => {
    if (selected.length === 0 || creator === null) {
      return;
    }
    record({
      supporting_evidence: selected,
      creator,
      confidence: confidence / 100,
      status: "validated",
      related_entities: entities
        .split(",")
        .map((value) => value.trim())
        .filter((value) => value.length > 0),
    });
    setSelected([]);
    setEntities("");
  };

  if (evidence.length === 0) {
    return (
      <p className="text-xs leading-relaxed text-ink-2">
        Attach evidence first. A finding is a conclusion, and the platform will
        not store one that nothing supports.
      </p>
    );
  }

  return (
    <div className="grid gap-3">
      <p className="text-xs leading-relaxed text-ink-2">
        Pick the evidence that supports your conclusion. Recording it here marks
        it <span className="font-semibold text-ink">validated</span> — you
        weighed the evidence yourself.
      </p>

      <fieldset className="grid gap-1.5">
        <legend className="mono-label uppercase text-ink-3">
          Supporting evidence
        </legend>
        {evidence.map((item) => (
          <label
            key={item.id}
            className="flex cursor-pointer items-start gap-2.5 rounded-input px-2.5 py-2 hover:bg-paper-2"
          >
            <input
              type="checkbox"
              checked={selected.includes(item.id)}
              onChange={() => toggle(item.id)}
              className="mt-0.5 h-4 w-4 shrink-0 accent-[var(--color-lav)]"
            />
            <span className="min-w-0">
              <span className="mono-label text-cyan-ink">{item.source}</span>
              <span className="ml-2 text-[0.8125rem] text-ink-2">
                {item.content}
              </span>
            </span>
          </label>
        ))}
      </fieldset>

      <div className="flex flex-wrap items-center gap-x-4 gap-y-3">
        <label className="flex items-center gap-2.5 text-[0.8125rem] text-ink-2">
          Confidence
          <input
            type="range"
            min={0}
            max={100}
            step={5}
            value={confidence}
            aria-label="Finding confidence"
            className="w-36 accent-[var(--color-lav)]"
            onChange={(event) => setConfidence(Number(event.target.value))}
          />
          <span className="mono-label w-9 tabular-nums font-semibold text-ink">
            {confidence}%
          </span>
        </label>
        <input
          aria-label="Related entities"
          placeholder="Related entity ids (optional, comma-separated)"
          value={entities}
          className="input min-w-40 flex-1"
          onChange={(event) => setEntities(event.target.value)}
        />
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <Button
          variant="soft"
          onClick={submit}
          busy={recording}
          disabled={selected.length === 0 || creator === null}
        >
          {recording ? "Recording…" : "Record finding"}
        </Button>
        {selected.length === 0 && (
          <span className="text-xs text-ink-3">
            Select at least one piece of evidence.
          </span>
        )}
      </div>

      {error && (
        <p
          role="alert"
          className="rounded-input border border-coral/50 bg-coral/10 px-3 py-2 text-xs text-coral-ink"
        >
          Could not record the finding ({error.code}).
        </p>
      )}
    </div>
  );
}

export function FindingsSection({
  findings,
  investigationId,
  evidence,
}: FindingsSectionProps) {
  const { state, dispatch } = useWorkspaceContext();

  return (
    <WorkspaceRegion
      title="Findings"
      note="Conclusions drawn from the evidence — by you or by an agent. Select one to see exactly which evidence backs it."
    >
      {findings.length === 0 ? (
        <Empty>
          No confirmed findings yet. A finding is a conclusion; the evidence
          underneath it is what makes it one.
        </Empty>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2">
          {findings.map((finding) => (
            <WorkspaceFindingCard
              key={finding.id}
              finding={finding}
              selected={state.selectedFindingId === finding.id}
              onSelect={(findingId) =>
                dispatch({ type: "SELECT_FINDING", findingId })
              }
            />
          ))}
        </div>
      )}

      <div className="mt-5 border-t border-line pt-4">
        <Disclosure
          summary="Record a finding"
          defaultOpen={findings.length === 0 && evidence.length > 0}
        >
          <RecordFindingForm
            investigationId={investigationId}
            evidence={evidence}
          />
        </Disclosure>
      </div>
    </WorkspaceRegion>
  );
}
