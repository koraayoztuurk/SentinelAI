// Confidence indicator component.
//
// Visualizes a confidence estimate (0..1) as both a bar and an explicit
// percentage label, so the value never relies on colour alone (accessibility,
// Frontend Architecture §17).
//
// The bar's colour is a reading of the number, not decoration: a low-confidence
// finding presented in the same green as a high-confidence one would quietly
// overstate it.

export interface ConfidenceIndicatorProps {
  readonly value: number;
  /** Optional caption; defaults to none so the component stays reusable. */
  readonly label?: string;
}

function tone(percent: number): string {
  if (percent >= 75) return "var(--color-mint)";
  if (percent >= 45) return "var(--color-pear)";
  return "var(--color-amber)";
}

export function ConfidenceIndicator({
  value,
  label,
}: ConfidenceIndicatorProps) {
  const clamped = Math.min(Math.max(value, 0), 1);
  const percent = Math.round(clamped * 100);
  return (
    <div className="grid gap-1.5" aria-label={`Confidence ${percent}%`}>
      <div className="flex items-baseline justify-between gap-2">
        <span className="mono-label uppercase text-ink-3">
          {label ?? "confidence"}
        </span>
        <span className="mono-label font-semibold tabular-nums text-ink">
          {percent}%
        </span>
      </div>
      {/* The fill is full-width and scaled on the X axis: animating `width`
          would run layout on every frame, `transform` runs on the compositor. */}
      <div className="meter">
        <div
          className="meter-fill"
          style={{
            ["--meter-value" as string]: clamped,
            ["--meter-tone" as string]: tone(percent),
          }}
        />
      </div>
    </div>
  );
}
