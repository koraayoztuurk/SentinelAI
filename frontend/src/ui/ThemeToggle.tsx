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
      className="btn btn-ghost mono-label px-2.5 py-1.5"
      onClick={toggleTheme}
    >
      Theme: {theme}
    </Button>
  );
}
