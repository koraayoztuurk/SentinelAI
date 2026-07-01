// Application entry point.
//
// In development, the Mock Service Worker is started before rendering so the app
// runs against a mocked Backend API. The worker is dynamically imported and guarded
// by `import.meta.env.DEV`, so it is never included in the production bundle.

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./app/App";
import "./index.css";

async function enableMocking(): Promise<void> {
  if (!import.meta.env.DEV) {
    return;
  }
  const { worker } = await import("./mocks/browser");
  await worker.start({ onUnhandledRequest: "bypass" });
}

const rootElement = document.getElementById("root");
if (rootElement === null) {
  throw new Error("Root element #root was not found.");
}

void enableMocking().then(() => {
  createRoot(rootElement).render(
    <StrictMode>
      <App />
    </StrictMode>,
  );
});
