// Primitive UI: Region.
//
// The titled surface every dashboard and workspace region sits on.
//
// The `note` is the point of this component, not decoration: a console that
// explains itself in one plain sentence per region is what separates a tool an
// analyst trusts from one they tolerate. Every region states what it holds and
// why it matters, in words that assume no prior knowledge of the platform.
//
// `tone` tints the surface with the accent that owns that kind of content —
// lavender for AI activity, cyan for evidence, coral for destructive things.
// Each accent owns its own surface; they are never blended.

import type { ReactNode } from "react";

export type RegionTone = "plain" | "ai" | "evidence" | "danger" | "quiet";

const TONES: Record<RegionTone, string> = {
  plain: "surface",
  ai: "surface surface-lav",
  evidence: "surface surface-cyan",
  danger: "surface surface-coral",
  quiet: "surface surface-quiet",
};

export interface RegionProps {
  readonly title: string;
  readonly note?: string;
  readonly action?: ReactNode;
  readonly tone?: RegionTone;
  readonly children: ReactNode;
}

export function Region({
  title,
  note,
  action,
  tone = "plain",
  children,
}: RegionProps) {
  return (
    <section className={`${TONES[tone]} p-5 sm:p-6`}>
      <div className="region-head">
        <div className="min-w-0">
          <h2 className="region-title">{title}</h2>
          {note && <p className="region-note">{note}</p>}
        </div>
        {action && <div className="flex shrink-0 items-center gap-2">{action}</div>}
      </div>
      <div className="mt-5">{children}</div>
    </section>
  );
}

export interface EmptyProps {
  readonly children: ReactNode;
}

/** The shared empty state: a quiet, bordered box rather than a bare grey line. */
export function Empty({ children }: EmptyProps) {
  return (
    <p className="rounded-input border border-dashed border-line-2 px-4 py-6 text-center text-sm text-ink-2">
      {children}
    </p>
  );
}
