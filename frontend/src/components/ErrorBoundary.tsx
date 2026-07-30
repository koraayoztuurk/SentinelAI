// Error boundary.
//
// Isolates failures so a localized error never terminates the whole user
// experience (Frontend Architecture §11). The foundation provides a minimal
// recovery surface; richer recovery flows are introduced by later specifications.

import { Component, type ErrorInfo, type ReactNode } from "react";

interface ErrorBoundaryProps {
  readonly children: ReactNode;
}

interface ErrorBoundaryState {
  readonly hasError: boolean;
}

export class ErrorBoundary extends Component<
  ErrorBoundaryProps,
  ErrorBoundaryState
> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(): ErrorBoundaryState {
    return { hasError: true };
  }

  override componentDidCatch(error: Error, info: ErrorInfo): void {
    // Observability: unexpected failures remain diagnosable without exposing
    // sensitive details to analysts (§11/§16).
    console.error("Unhandled UI error", error, info.componentStack);
  }

  override render(): ReactNode {
    if (this.state.hasError) {
      return (
        <div
          role="alert"
          className="rise m-6 rounded-card border border-coral/50 bg-coral/10 p-5"
        >
          <p className="text-sm font-semibold text-coral-ink">
            Something went wrong in this view.
          </p>
          <p className="mt-1 text-[0.8125rem] text-ink-2">
            Reloading the page will restore it. The investigation itself is not
            affected — nothing is stored in the browser.
          </p>
        </div>
      );
    }
    return this.props.children;
  }
}
