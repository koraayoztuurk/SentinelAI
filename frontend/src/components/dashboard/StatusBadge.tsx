// Status badge component.
//
// Renders an investigation, finding or memory status. Status is conveyed
// through the text label (not colour alone) for accessibility (Frontend
// Architecture §17); the tone map only reinforces it. Unknown statuses fall
// back to the neutral tone.
//
// The tone map is also a semantic contract: coral means danger and nothing
// else, so an erased or rejected thing is unmistakable next to a merely closed
// one. Mint is confirmed, amber is attention, cyan is in-progress, lavender is
// AI-produced.

const TONES: Record<string, string> = {
  created: "text-cyan-ink",
  active: "text-cyan-ink",
  running: "text-cyan-ink",
  proposed: "text-cyan-ink",
  candidate: "text-cyan-ink",
  synthesized: "text-lav-ink",
  validated: "text-mint-ink",
  accepted: "text-mint-ink",
  verified: "text-mint-ink",
  completed: "text-mint-ink",
  organizational: "text-mint-ink",
  escalated: "text-amber-ink",
  contained: "text-amber-ink",
  suspended: "text-amber-ink",
  exhausted: "text-amber-ink",
  rejected: "text-coral-ink",
  failed: "text-coral-ink",
  // Terminal end-of-life (ADR-017): a destructive, irreversible state — the
  // danger tone marks it as distinct from a settled "closed".
  erased: "text-coral-ink",
  closed: "text-ink-2",
  archived: "text-ink-2",
  deprecated: "text-ink-2",
};

const NEUTRAL = "text-ink-2";

export interface StatusBadgeProps {
  readonly status: string;
}

export function StatusBadge({ status }: StatusBadgeProps) {
  const tone = TONES[status.toLowerCase()] ?? NEUTRAL;
  return (
    <span className={`tag shrink-0 ${tone}`}>
      <span className="tag-dot" aria-hidden="true" />
      {status}
    </span>
  );
}
