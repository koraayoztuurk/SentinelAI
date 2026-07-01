// Application root.
//
// Composes the global providers, the top-level error boundary and the router —
// the Application layer's initialization responsibility (Frontend Architecture
// §7). It owns no business logic.

import { RouterProvider } from "react-router-dom";
import { ErrorBoundary } from "../components/ErrorBoundary";
import { Providers } from "./providers";
import { router } from "./router";

export function App() {
  return (
    <ErrorBoundary>
      <Providers>
        <RouterProvider router={router} />
      </Providers>
    </ErrorBoundary>
  );
}
