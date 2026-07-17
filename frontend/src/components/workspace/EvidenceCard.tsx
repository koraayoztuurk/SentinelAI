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
  // Present only for evidence with a downloadable payload (ES-061).
  readonly onDownload?: (evidenceId: string) => void;
  readonly downloading?: boolean;
}

export function EvidenceCard({
  evidence,
  selected,
  highlighted,
  onSelect,
  onDownload,
  downloading = false,
}: EvidenceCardProps) {
  const border = selected
    ? "border-[var(--color-accent)]"
    : highlighted
      ? "border-amber-400/70"
      : "border-white/10";
  // The selection control is a button, so the download control cannot nest
  // inside it (no nested interactive elements); they are siblings in a card.
  return (
    <div className={`rounded-lg border ${border} bg-white/5`}>
      <button
        type="button"
        aria-pressed={selected}
        onClick={() => onSelect(evidence.id)}
        className="w-full p-4 text-left"
      >
        <div className="flex items-center justify-between gap-3">
          <span className="font-mono text-xs opacity-70">{evidence.id}</span>
          <span className="text-xs opacity-60">{evidence.source}</span>
        </div>
        <p className="mt-2 line-clamp-2 text-sm">{evidence.content}</p>
        <div className="mt-2 flex items-center gap-2 text-xs opacity-60">
          <span className="truncate">{evidence.integrity}</span>
          <span>·</span>
          <span>{evidence.timestamp}</span>
          {highlighted && (
            <span className="ml-auto text-amber-300">supports finding</span>
          )}
        </div>
      </button>
      {evidence.downloadable && onDownload && (
        <div className="border-t border-white/10 px-4 py-2">
          <button
            type="button"
            onClick={() => onDownload(evidence.id)}
            disabled={downloading}
            className="text-xs text-[var(--color-accent)] disabled:opacity-40"
          >
            {downloading ? "Downloading…" : "Download payload"}
          </button>
        </div>
      )}
    </div>
  );
}
