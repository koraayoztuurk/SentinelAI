// Application entry point.
//
// The app talks to the real Backend API (ES-047): in development the Vite dev
// server proxies `/api` to the local backend, in containers nginx does — no
// mocking layer runs in the browser. The api client's pluggable token source
// is bound here to the persisted development credential (ES-046 dev auth).

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./app/App";
import { setAuthTokenSource } from "./communication/apiClient";
import { getDevAuthCredential } from "./state/devAuth";
import "./index.css";

setAuthTokenSource(getDevAuthCredential);

const rootElement = document.getElementById("root");
if (rootElement === null) {
  throw new Error("Root element #root was not found.");
}

createRoot(rootElement).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
