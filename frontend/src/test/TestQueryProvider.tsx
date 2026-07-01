// Test helper: wraps a tree in a fresh QueryClient (retry disabled via
// `createQueryClient`) so hooks that use TanStack Query can render in isolation. A
// new client per mount keeps tests independent (no cache bleed between tests).

import { useState, type ReactNode } from "react";
import { QueryClientProvider } from "@tanstack/react-query";
import { createQueryClient } from "../state/query";

export function TestQueryProvider({ children }: { readonly children: ReactNode }) {
  const [client] = useState(createQueryClient);
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}
