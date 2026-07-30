// Records an opened investigation into Session State (recent list).
//
// Mounted by the pages that display an investigation, so the recent list is a
// by-product of actually opening one rather than something the analyst has to
// curate. It records only after the title has loaded — an entry with a blank
// label would be worse than no entry.

import { useEffect } from "react";
import { rememberInvestigation } from "./recentInvestigations";

export function useRememberInvestigation(
  investigationId: string,
  title: string | undefined,
): void {
  useEffect(() => {
    if (investigationId.trim().length === 0 || title === undefined) {
      return;
    }
    // The timestamp is supplied here rather than inside the store, mirroring
    // the platform's caller-supplies-timestamps discipline.
    rememberInvestigation(investigationId, title, new Date().toISOString());
  }, [investigationId, title]);
}
