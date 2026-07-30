// Main application layout.
//
// Establishes consistent page organization (Frontend Architecture §7): a single
// warm wash anchored to the top of the page, an edge-aligned sticky header
// carrying the wordmark and session controls, the main content region and one
// inline footer line. Structure only — pages own their content.

import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { DevTokenField } from "../ui/DevTokenField";
import { ThemeToggle } from "../ui/ThemeToggle";

export interface MainLayoutProps {
  readonly children: ReactNode;
}

export function MainLayout({ children }: MainLayoutProps) {
  return (
    <div className="flex min-h-screen flex-col">
      <div className="wash" aria-hidden="true" />

      <header className="topbar">
        <div className="shell flex flex-wrap items-center justify-between gap-x-4 gap-y-2 py-3">
          <Link
            to="/"
            className="flex min-w-0 items-center gap-2.5 no-underline"
            aria-label="SentinelAI home"
          >
            <span className="brandmark" aria-hidden="true" />
            <span className="text-[0.95rem] font-bold tracking-tight text-ink">
              SentinelAI
            </span>
            <span className="mono-label hidden text-ink-3 sm:inline">
              investigation console
            </span>
          </Link>
          <div className="flex min-w-0 items-center gap-2">
            <DevTokenField />
            <ThemeToggle />
          </div>
        </div>
      </header>

      {/* `min-w-0`: a flex item defaults to `min-width: auto`, which lets a
          wide descendant (the tab rail, a long identifier) push the whole page
          past the viewport instead of scrolling inside its own box. */}
      <main className="shell min-w-0 flex-1 py-8 sm:py-10">{children}</main>

      <footer className="mt-8 border-t border-line">
        <div className="shell flex flex-wrap items-center gap-x-3 gap-y-1 py-4">
          <span className="text-xs text-ink-2">
            SentinelAI — AI-assisted cyber investigations.
          </span>
          <span className="text-xs text-ink-3">
            Recommendations are advisory; the analyst decides.
          </span>
        </div>
      </footer>
    </div>
  );
}
