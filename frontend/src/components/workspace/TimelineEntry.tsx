// Timeline entry component.
//
// Presents a single derived timeline event (evidence collected or finding recorded)
// on a vertical rail, in chronological order. The entry is emphasized when it refers
// to the currently selected artifact, keeping the timeline synchronized with the
// shared Investigation Context.

import type { TimelineEventViewModel } from "../../communication/workspace";

export interface TimelineEntryProps {
  readonly event: TimelineEventViewModel;
  readonly emphasized: boolean;
}

const KIND_LABEL: Record<TimelineEventViewModel["kind"], string> = {
  evidence: "Evidence",
  finding: "Finding",
};

const KIND_TONE: Record<TimelineEventViewModel["kind"], string> = {
  evidence: "text-cyan-ink",
  finding: "text-mint-ink",
};

export function TimelineEntry({ event, emphasized }: TimelineEntryProps) {
  return (
    <li
      className={`relative grid grid-cols-[minmax(0,1fr)] gap-1 rounded-input py-2.5 pl-7 pr-3 transition-colors duration-200 sm:grid-cols-[13rem_minmax(0,1fr)] sm:items-baseline sm:gap-3 ${
        emphasized ? "bg-paper-3" : "hover:bg-paper-2"
      }`}
    >
      {/* Rail + event node */}
      <span
        aria-hidden="true"
        className="absolute bottom-0 left-2.5 top-0 w-px bg-line"
      />
      <span
        aria-hidden="true"
        className={`absolute left-2.5 top-4 h-2 w-2 -translate-x-1/2 rounded-pill ring-4 ring-paper ${
          event.kind === "evidence" ? "bg-cyan" : "bg-mint"
        }`}
      />
      <span
        className="mono-label truncate tabular-nums text-ink-3"
        title={event.occurredAt}
      >
        {event.occurredAt}
      </span>
      <span className="flex min-w-0 flex-wrap items-baseline gap-x-2 gap-y-1">
        <span className={`mono-label font-semibold ${KIND_TONE[event.kind]}`}>
          {KIND_LABEL[event.kind]}
        </span>
        <span className="min-w-0 truncate text-sm">{event.label}</span>
        <span className="mono-label ml-auto shrink-0 text-ink-3">
          {event.reference}
        </span>
      </span>
    </li>
  );
}
