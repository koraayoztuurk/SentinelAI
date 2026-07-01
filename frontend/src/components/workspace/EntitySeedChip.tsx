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
  const border = active
    ? "border-[var(--color-accent)]"
    : "border-white/20";
  return (
    <button
      type="button"
      aria-pressed={active}
      onClick={() => onSelect(entityId)}
      className={`rounded-full border ${border} bg-white/5 px-3 py-1 font-mono text-xs`}
    >
      {entityId}
    </button>
  );
}
