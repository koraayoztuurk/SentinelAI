// Global providers.
//
// The single place to compose application-wide context providers (Application
// layer, Frontend Architecture §7). The foundation keeps this minimal; state and
// server-cache providers are introduced by the State Management specification
// (ES-027).

import type { ReactNode } from "react";

export interface ProvidersProps {
  readonly children: ReactNode;
}

export function Providers({ children }: ProvidersProps) {
  return <>{children}</>;
}
