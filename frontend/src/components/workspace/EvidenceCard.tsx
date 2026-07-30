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
  const state = selected ? "card-selected" : highlighted ? "card-linked" : "";
  // The selection control is a button, so the download control cannot nest
  // inside it (no nested interactive elements); they are siblings in a card.
  return (
    <div className={`card ${state}`}>
      <button
        type="button"
        aria-pressed={selected}
        onClick={() => onSelect(evidence.id)}
        className="w-full cursor-pointer rounded-input p-4 text-left"
      >
        <div className="flex items-center justify-between gap-3">
          <span className="tag text-cyan-ink">
            <span className="tag-dot" aria-hidden="true" />
            {evidence.source}
          </span>
          {highlighted && (
            <span className="mono-label font-semibold text-cyan-ink">
              supports finding
            </span>
          )}
        </div>
        <p className="mt-2.5 line-clamp-3 text-sm leading-relaxed">
          {evidence.content}
        </p>
        <div className="mono-label mt-3 flex flex-wrap items-center gap-x-2 gap-y-1 text-ink-3">
          <span className="truncate" title={evidence.id}>
            {evidence.id}
          </span>
          <span aria-hidden="true">·</span>
          <span className="truncate">{evidence.integrity}</span>
          <span aria-hidden="true">·</span>
          <span className="tabular-nums">{evidence.timestamp}</span>
        </div>
      </button>
      {evidence.downloadable && onDownload && (
        <div className="border-t border-line px-4 py-2.5">
          <button
            type="button"
            onClick={() => onDownload(evidence.id)}
            disabled={downloading}
            className="link mono-label disabled:cursor-not-allowed disabled:opacity-40"
          >
            {downloading ? "Downloading…" : "Download payload"}
          </button>
        </div>
      )}
    </div>
  );
}
