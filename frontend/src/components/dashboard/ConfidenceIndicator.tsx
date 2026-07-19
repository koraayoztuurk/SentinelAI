// Confidence indicator component.
//
// Visualizes a confidence estimate (0..1) as both an animated bar and an explicit
// percentage label, so the value never relies on colour alone (accessibility,
// Frontend Architecture §17).

export interface ConfidenceIndicatorProps {
  readonly value: number;
}

export function ConfidenceIndicator({ value }: ConfidenceIndicatorProps) {
  const clamped = Math.min(Math.max(value, 0), 1);
  const percent = Math.round(clamped * 100);
  return (
    <div className="flex items-center gap-2" aria-label={`Confidence ${percent}%`}>
      <div className="meter w-24">
        <div className="meter-fill" style={{ width: `${percent}%` }} />
      </div>
      <span className="mono-label tabular-nums text-muted">{percent}%</span>
    </div>
  );
}
