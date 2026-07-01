// Global providers.
//
// The single place to compose application-wide state stores (Application layer,
// Frontend Architecture §7): the server-state client (TanStack Query, behind the
// `state/query` boundary) and the app-level Session State store. The Investigation
// Context stays workspace-scoped (mounted by the workspace page), consistent with
// its owner (UI State Management §6).

import { useState, type ReactNode } from "react";
import { QueryClientProvider } from "@tanstack/react-query";
import { createQueryClient } from "../state/query";
import { SessionProvider } from "../state/session";

export interface ProvidersProps {
  readonly children: ReactNode;
}

export function Providers({ children }: ProvidersProps) {
  const [queryClient] = useState(createQueryClient);
  return (
    <QueryClientProvider client={queryClient}>
      <SessionProvider>{children}</SessionProvider>
    </QueryClientProvider>
  );
}
