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
      className="chip"
    >
      {active && <span className="tag-dot" aria-hidden="true" />}
      {entityId}
    </button>
  );
}
