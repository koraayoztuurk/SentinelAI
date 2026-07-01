// Theme toggle (PrimitiveUI).
//
// Reads and flips the Session State theme. The label conveys the current theme as
// text (not an icon alone) for accessibility (Frontend Architecture §17).

import { useSession } from "../state/session";
import { Button } from "./Button";

export function ThemeToggle() {
  const { theme, toggleTheme } = useSession();
  return (
    <Button
      className="rounded border border-white/20 px-2.5 py-1 text-xs"
      onClick={toggleTheme}
    >
      Theme: {theme}
    </Button>
  );
}
