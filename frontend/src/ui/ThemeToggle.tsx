// Theme toggle (PrimitiveUI).
//
// Reads and flips the Session State theme. The label conveys the current theme
// as text (not an icon alone) for accessibility (Frontend Architecture §17); the
// drawn mark alongside it is decorative and hidden from assistive technology.

import { useSession } from "../state/session";
import { Button } from "./Button";

export function ThemeToggle() {
  const { theme, toggleTheme } = useSession();
  return (
    <Button
      variant="outline"
      className="btn-sm mono-label"
      onClick={toggleTheme}
      title="Switch between the light and dark console"
    >
      <span
        aria-hidden="true"
        className={`inline-block h-2.5 w-2.5 rounded-pill ${
          theme === "dark"
            ? "bg-transparent shadow-[inset_-3px_0_0_0_currentColor]"
            : "bg-current"
        }`}
      />
      {/* The word is dropped on narrow screens; the mark and the value still
          carry the state, and `textContent` is unchanged for assistive tech. */}
      <span className="hidden sm:inline">Theme:</span> {theme}
    </Button>
  );
}
