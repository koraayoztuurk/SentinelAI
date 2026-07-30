// Primitive UI: Button.
//
// The lowest architectural layer (Frontend Architecture §7): a reusable element
// with no SentinelAI-specific business knowledge.
//
// The button is one system with style variants. The press is the feedback: it
// lifts on hover and physically depresses on :active — no scale, no spring
// overshoot. `variant` selects the style; `className` still passes through, so
// every existing call site keeps working unchanged.

import type { ReactNode } from "react";

export type ButtonVariant = "primary" | "soft" | "outline" | "danger" | "link";

const VARIANTS: Record<ButtonVariant, string> = {
  primary: "btn",
  soft: "btn btn-soft",
  outline: "btn btn-outline",
  danger: "btn btn-danger",
  link: "link",
};

export interface ButtonProps {
  readonly children: ReactNode;
  readonly onClick?: () => void;
  readonly disabled?: boolean;
  readonly className?: string;
  readonly variant?: ButtonVariant;
  /** Renders a spinner and blocks input while an action is in flight. */
  readonly busy?: boolean;
  readonly title?: string;
}

export function Button({
  children,
  onClick,
  disabled,
  className,
  variant,
  busy = false,
  title,
}: ButtonProps) {
  const classes = [variant ? VARIANTS[variant] : "", className]
    .filter(Boolean)
    .join(" ");

  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled || busy}
      className={classes === "" ? undefined : classes}
      title={title}
      aria-busy={busy || undefined}
    >
      {busy && <span className="spinner" aria-hidden="true" />}
      {children}
    </button>
  );
}
