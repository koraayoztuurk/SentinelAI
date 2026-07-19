// Main application layout.
//
// Establishes consistent page organization (Frontend Architecture §7): an
// ambient background, a frosted sticky header with the brand mark and session
// controls, the main content region and a slim status footer. Structure only —
// pages own their content.

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
      <div className="ambient" aria-hidden="true" />

      <header className="app-header">
        <div className="mx-auto flex w-full max-w-6xl items-center justify-between gap-4 px-6 py-3">
          <Link
            to="/"
            className="group flex items-center gap-2.5 no-underline"
            aria-label="SentinelAI home"
          >
            <span className="status-dot" aria-hidden="true" />
            <span className="text-sm font-bold tracking-[0.22em] uppercase">
              Sentinel
              <span className="text-accent transition-colors group-hover:text-ink">
                AI
              </span>
            </span>
            <span className="mono-label hidden text-faint sm:inline">
              // investigation console
            </span>
          </Link>
          <div className="flex items-center gap-3">
            <DevTokenField />
            <ThemeToggle />
          </div>
        </div>
      </header>

      <main className="mx-auto w-full max-w-6xl flex-1 px-6 py-8">
        {children}
      </main>

      <footer className="border-t border-line">
        <div className="mx-auto flex w-full max-w-6xl items-center justify-between px-6 py-3">
          <span className="mono-label text-faint">
            SentinelAI · AI-assisted cyber investigations
          </span>
          <span className="mono-label flex items-center gap-2 text-faint">
            <span
              className="inline-block h-1.5 w-1.5 rounded-full bg-ok"
              aria-hidden="true"
            />
            console ready
          </span>
        </div>
      </footer>
    </div>
  );
}
