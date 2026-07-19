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
  const state = selected
    ? "card-selected"
    : highlighted
      ? "card-highlighted"
      : "";
  // The selection control is a button, so the download control cannot nest
  // inside it (no nested interactive elements); they are siblings in a card.
  return (
    <div className={`card ${state}`}>
      <button
        type="button"
        aria-pressed={selected}
        onClick={() => onSelect(evidence.id)}
        className="w-full cursor-pointer p-4 text-left"
      >
        <div className="flex items-center justify-between gap-3">
          <span
            className="mono-label min-w-0 truncate text-faint"
            title={evidence.id}
          >
            {evidence.id}
          </span>
          <span className="mono-label shrink-0 whitespace-nowrap rounded border border-line bg-panel-2/60 px-1.5 py-0.5 uppercase text-muted">
            {evidence.source}
          </span>
        </div>
        <p className="mt-2 line-clamp-2 text-sm">{evidence.content}</p>
        <div className="mono-label mt-2 flex items-center gap-2 text-faint">
          <span className="truncate">{evidence.integrity}</span>
          <span aria-hidden="true">·</span>
          <span>{evidence.timestamp}</span>
          {highlighted && (
            <span className="ml-auto font-semibold text-warn">
              supports finding
            </span>
          )}
        </div>
      </button>
      {evidence.downloadable && onDownload && (
        <div className="border-t border-line px-4 py-2">
          <button
            type="button"
            onClick={() => onDownload(evidence.id)}
            disabled={downloading}
            className="btn-link mono-label cursor-pointer disabled:cursor-not-allowed disabled:opacity-40"
          >
            {downloading ? "Downloading…" : "Download payload"}
          </button>
        </div>
      )}
    </div>
  );
}
