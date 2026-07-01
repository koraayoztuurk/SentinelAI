// Mocked Backend API handlers (dev + tests only).
//
// MSW intercepts the requests the `apiClient` makes to the Backend API and returns
// the standard ES-014 response envelope, so the dashboard renders against
// realistic data without a running backend. An unknown investigation id yields the
// error envelope so error states can be exercised.

import { http, HttpResponse } from "msw";
import { getApiBaseUrl } from "../communication/config";
import {
  SAMPLE_INVESTIGATION_ID,
  sampleFindings,
  sampleInvestigation,
} from "./data";

const base = getApiBaseUrl();

function meta() {
  return {
    request_id: "mock-req",
    correlation_id: "mock-req",
    timestamp: new Date().toISOString(),
    api_version: "v1",
  };
}

export const handlers = [
  http.get(`${base}/api/v1/investigations/:id`, ({ params }) => {
    if (params.id !== SAMPLE_INVESTIGATION_ID) {
      return HttpResponse.json(
        {
          status: "error",
          error: { code: "investigation.not_found", message: "Investigation not found." },
          meta: meta(),
        },
        { status: 404 },
      );
    }
    return HttpResponse.json({
      status: "success",
      data: sampleInvestigation,
      meta: meta(),
    });
  }),

  http.get(`${base}/api/v1/investigations/:id/findings`, ({ params }) => {
    if (params.id !== SAMPLE_INVESTIGATION_ID) {
      return HttpResponse.json(
        {
          status: "error",
          error: { code: "investigation.not_found", message: "Investigation not found." },
          meta: meta(),
        },
        { status: 404 },
      );
    }
    return HttpResponse.json({
      status: "success",
      data: sampleFindings,
      meta: meta(),
    });
  }),
];
