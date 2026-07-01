// Main application layout.
//
// Establishes consistent page organization (Frontend Architecture §7): a header
// and a main content region. The foundation defines structure only; the
// investigation workspace regions (navigation, side/context panels) are
// introduced by later specifications (ES-024+).

import type { ReactNode } from "react";

export interface MainLayoutProps {
  readonly children: ReactNode;
}

export function MainLayout({ children }: MainLayoutProps) {
  return (
    <div className="min-h-screen flex flex-col">
      <header className="px-6 py-4 border-b border-white/10">
        <span className="font-semibold">SentinelAI</span>
      </header>
      <main className="flex-1 p-6">{children}</main>
    </div>
  );
}
