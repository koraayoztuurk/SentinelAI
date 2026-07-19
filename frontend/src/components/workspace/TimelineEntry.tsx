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

const KIND_DOT: Record<TimelineEventViewModel["kind"], string> = {
  evidence: "bg-info",
  finding: "bg-accent",
};

export function TimelineEntry({ event, emphasized }: TimelineEntryProps) {
  return (
    <li
      className={`relative flex items-baseline gap-3 rounded-md py-1.5 pl-6 pr-2 transition-colors duration-200 ${
        emphasized ? "bg-raise/70" : "hover:bg-panel-2/50"
      }`}
    >
      {/* Rail + event node */}
      <span
        aria-hidden="true"
        className="absolute left-2 top-0 bottom-0 w-px bg-line"
      />
      <span
        aria-hidden="true"
        className={`absolute left-2 top-1/2 h-2 w-2 -translate-x-1/2 -translate-y-1/2 rounded-full ${KIND_DOT[event.kind]} ${
          emphasized ? "glow-breathe" : ""
        }`}
      />
      <span
        className="mono-label w-48 shrink-0 truncate whitespace-nowrap tabular-nums text-faint"
        title={event.occurredAt}
      >
        {event.occurredAt}
      </span>
      <span className="mono-label uppercase text-muted">
        {KIND_LABEL[event.kind]}
      </span>
      <span className="text-sm">{event.label}</span>
      <span className="mono-label ml-auto text-faint">{event.reference}</span>
    </li>
  );
}
