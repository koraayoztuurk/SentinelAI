// Evidence card component.
//
// Presents a single evidence item and participates in two selection cues: it is
// `selected` when the analyst picked it directly, and `highlighted` when it supports
// the currently selected finding (cross-region synchronization, interaction-model
// §5 Highlighting). Selection status is conveyed through text (not colour alone) for
// accessibility (Frontend Architecture §17).

import type { EvidenceViewModel } from "../../communication/workspace";

export interface EvidenceCardProps {
  readonly evidence: EvidenceViewModel;
  readonly selected: boolean;
  readonly highlighted: boolean;
  readonly onSelect: (evidenceId: string) => void;
}

export function EvidenceCard({
  evidence,
  selected,
  highlighted,
  onSelect,
}: EvidenceCardProps) {
  const border = selected
    ? "border-[var(--color-accent)]"
    : highlighted
      ? "border-amber-400/70"
      : "border-white/10";
  return (
    <button
      type="button"
      aria-pressed={selected}
      onClick={() => onSelect(evidence.id)}
      className={`w-full rounded-lg border ${border} bg-white/5 p-4 text-left`}
    >
      <div className="flex items-center justify-between gap-3">
        <span className="font-mono text-xs opacity-70">{evidence.id}</span>
        <span className="text-xs opacity-60">{evidence.source}</span>
      </div>
      <p className="mt-2 line-clamp-2 text-sm">{evidence.content}</p>
      <div className="mt-2 flex items-center gap-2 text-xs opacity-60">
        <span>{evidence.integrity}</span>
        <span>·</span>
        <span>{evidence.timestamp}</span>
        {highlighted && (
          <span className="ml-auto text-amber-300">supports finding</span>
        )}
      </div>
    </button>
  );
}
