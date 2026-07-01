// Status badge component.
//
// Renders an investigation or finding status. Status is conveyed through the text
// label (not colour alone) for accessibility (Frontend Architecture §17).

export interface StatusBadgeProps {
  readonly status: string;
}

export function StatusBadge({ status }: StatusBadgeProps) {
  return (
    <span className="inline-flex items-center rounded-full border border-white/20 px-2.5 py-0.5 text-xs font-medium uppercase tracking-wide">
      {status}
    </span>
  );
}
