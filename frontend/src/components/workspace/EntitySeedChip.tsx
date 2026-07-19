// Entity seed chip component.
//
// A selectable entry point into the graph. The seeds are the entities referenced by
// the confirmed findings (ES-026); selecting one starts (or restarts) the graph
// exploration from that entity. The active seed is conveyed through text and border,
// not colour alone (accessibility, Frontend Architecture §17).

export interface EntitySeedChipProps {
  readonly entityId: string;
  readonly active: boolean;
  readonly onSelect: (entityId: string) => void;
}

export function EntitySeedChip({
  entityId,
  active,
  onSelect,
}: EntitySeedChipProps) {
  return (
    <button
      type="button"
      aria-pressed={active}
      onClick={() => onSelect(entityId)}
      className={`mono-label cursor-pointer rounded-full border px-3 py-1 transition-all duration-200 ${
        active
          ? "border-accent/70 bg-accent/10 text-accent shadow-[0_0_16px_-6px_var(--color-accent)]"
          : "border-line-strong bg-panel-2/60 text-muted hover:border-accent/40 hover:text-ink"
      }`}
    >
      {entityId}
    </button>
  );
}
