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
        <div role="alert" className="p-6">
          Something went wrong. Please reload the affected view.
        </div>
      );
    }
    return this.props.children;
  }
}
