// Status badge component.
//
// Renders an investigation or finding status. Status is conveyed through the text
// label (not colour alone) for accessibility (Frontend Architecture §17); the tone
// map only reinforces it. Unknown statuses fall back to the neutral tone.

const TONES: Record<string, string> = {
  created: "border-info/50 text-info [--pulse:var(--color-info)]",
  active: "border-accent/50 text-accent [--pulse:var(--color-accent)]",
  running: "border-accent/50 text-accent [--pulse:var(--color-accent)]",
  validated: "border-ok/50 text-ok [--pulse:var(--color-ok)]",
  accepted: "border-ok/50 text-ok [--pulse:var(--color-ok)]",
  verified: "border-ok/50 text-ok [--pulse:var(--color-ok)]",
  completed: "border-ok/50 text-ok [--pulse:var(--color-ok)]",
  proposed: "border-info/50 text-info [--pulse:var(--color-info)]",
  candidate: "border-info/50 text-info [--pulse:var(--color-info)]",
  escalated: "border-warn/60 text-warn [--pulse:var(--color-warn)]",
  contained: "border-warn/60 text-warn [--pulse:var(--color-warn)]",
  rejected: "border-danger/50 text-danger [--pulse:var(--color-danger)]",
  failed: "border-danger/50 text-danger [--pulse:var(--color-danger)]",
  closed: "border-line-strong text-muted [--pulse:var(--color-muted)]",
  deprecated: "border-line-strong text-muted [--pulse:var(--color-muted)]",
};

const NEUTRAL = "border-line-strong text-muted [--pulse:var(--color-muted)]";

export interface StatusBadgeProps {
  readonly status: string;
}

export function StatusBadge({ status }: StatusBadgeProps) {
  const tone = TONES[status.toLowerCase()] ?? NEUTRAL;
  return (
    <span
      className={`mono-label inline-flex shrink-0 items-center gap-1.5 whitespace-nowrap rounded-full border bg-panel-2/60 px-2.5 py-0.5 font-medium uppercase ${tone}`}
    >
      <span className="status-dot h-1.5 w-1.5" aria-hidden="true" />
      {status}
    </span>
  );
}
