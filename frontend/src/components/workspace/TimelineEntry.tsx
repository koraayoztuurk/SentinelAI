// Timeline entry component.
//
// Presents a single derived timeline event (evidence collected or finding recorded)
// in chronological order. The entry is emphasized when it refers to the currently
// selected artifact, keeping the timeline synchronized with the shared Investigation
// Context.

import type { TimelineEventViewModel } from "../../communication/workspace";

export interface TimelineEntryProps {
  readonly event: TimelineEventViewModel;
  readonly emphasized: boolean;
}

const KIND_LABEL: Record<TimelineEventViewModel["kind"], string> = {
  evidence: "Evidence",
  finding: "Finding",
};

export function TimelineEntry({ event, emphasized }: TimelineEntryProps) {
  return (
    <li
      className={`flex items-baseline gap-3 rounded-md px-2 py-1.5 ${
        emphasized ? "bg-white/10" : ""
      }`}
    >
      <span className="w-40 shrink-0 font-mono text-xs opacity-60">
        {event.occurredAt}
      </span>
      <span className="text-xs uppercase tracking-wide opacity-70">
        {KIND_LABEL[event.kind]}
      </span>
      <span className="text-sm">{event.label}</span>
      <span className="ml-auto font-mono text-xs opacity-50">
        {event.reference}
      </span>
    </li>
  );
}
