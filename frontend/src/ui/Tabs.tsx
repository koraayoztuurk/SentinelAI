// Primitive UI: Tabs.
//
// An accessible tab set following the WAI-ARIA tabs pattern: roving tabindex,
// Arrow/Home/End keyboard navigation, `aria-controls` / `aria-labelledby`
// wiring. Panels stay mounted so each region keeps its own state (a graph
// exploration survives a trip to the evidence tab); inactive panels carry the
// `hidden` attribute, so they leave the accessibility tree entirely.
//
// Presentation only — the active tab is owned by the caller, which keeps the
// component free of any investigation knowledge (Frontend Architecture §7).

import { useRef, type ReactNode } from "react";

export interface TabDefinition {
  readonly id: string;
  readonly label: string;
  /** Optional count rendered as a pill after the label (e.g. evidence items). */
  readonly count?: number;
}

export interface TabsProps {
  readonly tabs: readonly TabDefinition[];
  readonly active: string;
  readonly onChange: (id: string) => void;
  readonly label: string;
  readonly children: (tabId: string) => ReactNode;
}

export function Tabs({ tabs, active, onChange, label, children }: TabsProps) {
  const listRef = useRef<HTMLDivElement>(null);

  const focusTab = (index: number) => {
    const bounded = (index + tabs.length) % tabs.length;
    const target = tabs[bounded];
    if (target === undefined) {
      return;
    }
    onChange(target.id);
    listRef.current
      ?.querySelector<HTMLButtonElement>(`#tab-${CSS.escape(target.id)}`)
      ?.focus();
  };

  const onKeyDown = (event: React.KeyboardEvent, index: number) => {
    const moves: Record<string, number> = {
      ArrowRight: index + 1,
      ArrowLeft: index - 1,
      Home: 0,
      End: tabs.length - 1,
    };
    const next = moves[event.key];
    if (next === undefined) {
      return;
    }
    event.preventDefault();
    focusTab(next);
  };

  return (
    <>
      <div ref={listRef} role="tablist" aria-label={label} className="tablist">
        {tabs.map((tab, index) => {
          const selected = tab.id === active;
          return (
            <button
              key={tab.id}
              id={`tab-${tab.id}`}
              type="button"
              role="tab"
              className="tab"
              aria-selected={selected}
              aria-controls={`panel-${tab.id}`}
              tabIndex={selected ? 0 : -1}
              onClick={() => onChange(tab.id)}
              onKeyDown={(event) => onKeyDown(event, index)}
            >
              {tab.label}
              {tab.count !== undefined && tab.count > 0 && (
                <span className="tab-count">{tab.count}</span>
              )}
            </button>
          );
        })}
      </div>

      {tabs.map((tab) => (
        <div
          key={tab.id}
          id={`panel-${tab.id}`}
          role="tabpanel"
          aria-labelledby={`tab-${tab.id}`}
          tabIndex={0}
          hidden={tab.id !== active}
          className="mt-5 min-w-0 focus-visible:outline-offset-4"
        >
          {children(tab.id)}
        </div>
      ))}
    </>
  );
}
