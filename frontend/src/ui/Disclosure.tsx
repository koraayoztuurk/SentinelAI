// Primitive UI: Disclosure.
//
// A labelled show/hide region. Used wherever detail would otherwise crowd the
// surface — the explainer at the top of the workspace, the raw fields under a
// trace entry, the destructive controls in Data lifecycle.
//
// The content is unmounted when collapsed, which is the honest behaviour for a
// disclosure: nothing hidden is announced, nothing hidden is focusable.

import { useId, useState, type ReactNode } from "react";

export interface DisclosureProps {
  readonly summary: ReactNode;
  readonly children: ReactNode;
  readonly defaultOpen?: boolean;
  readonly className?: string;
}

export function Disclosure({
  summary,
  children,
  defaultOpen = false,
  className,
}: DisclosureProps) {
  const [open, setOpen] = useState(defaultOpen);
  const panelId = useId();

  return (
    <div className={className}>
      <button
        type="button"
        className="disclosure-trigger"
        aria-expanded={open}
        aria-controls={panelId}
        onClick={() => setOpen((value) => !value)}
      >
        <span className="disclosure-caret" aria-hidden="true" />
        {summary}
      </button>
      {open && (
        <div id={panelId} className="rise mt-3">
          {children}
        </div>
      )}
    </div>
  );
}
