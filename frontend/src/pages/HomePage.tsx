// Placeholder landing page.
//
// Provides an entry point into the investigation dashboard. The platform-level
// investigation list is introduced by a later specification (the backend exposes
// no list endpoint yet), so the foundation links to a representative investigation.

import { Link } from "react-router-dom";

// A representative investigation id for the landing entry point; the backend
// exposes no investigation-list endpoint yet (deferred).
const SAMPLE_INVESTIGATION_ID = "inv-001";

export function HomePage() {
  return (
    <section>
      <h1 className="text-xl font-semibold">SentinelAI</h1>
      <p className="mt-2 text-sm opacity-80">
        AI-assisted cybersecurity investigations.
      </p>
      <Link
        to={`/investigations/${SAMPLE_INVESTIGATION_ID}`}
        className="mt-4 inline-block rounded border border-white/20 px-3 py-1 text-sm"
      >
        Open sample investigation
      </Link>
    </section>
  );
}
