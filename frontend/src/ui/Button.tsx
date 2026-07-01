// Primitive UI: Button.
//
// The lowest architectural layer (Frontend Architecture §7): a reusable element
// with no SentinelAI-specific business knowledge. The foundation keeps it minimal
// (children / onClick / disabled / className); design-system features (variant,
// size, theme) are introduced by the dashboard/workspace specifications (ES-024+).

import type { ReactNode } from "react";

export interface ButtonProps {
  readonly children: ReactNode;
  readonly onClick?: () => void;
  readonly disabled?: boolean;
  readonly className?: string;
}

export function Button({ children, onClick, disabled, className }: ButtonProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={className}
    >
      {children}
    </button>
  );
}
