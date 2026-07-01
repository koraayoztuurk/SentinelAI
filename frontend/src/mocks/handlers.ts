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
  sampleEntities,
  sampleEvidence,
  sampleFindings,
  sampleInvestigation,
  sampleRelationships,
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

  http.get(`${base}/api/v1/investigations/:id/evidence`, ({ params }) => {
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
      data: sampleEvidence,
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

  // --- graph (entity-seeded; the handlers derive incidence/neighbours) ---

  http.get(`${base}/api/v1/graph/entities/:id`, ({ params }) => {
    const entity = sampleEntities.find((item) => item.id === params.id);
    if (entity === undefined) {
      return HttpResponse.json(
        {
          status: "error",
          error: { code: "graph.entity_not_found", message: "Entity not found." },
          meta: meta(),
        },
        { status: 404 },
      );
    }
    return HttpResponse.json({ status: "success", data: entity, meta: meta() });
  }),

  http.get(`${base}/api/v1/graph/entities/:id/relationships`, ({ params }) => {
    const incident = sampleRelationships.filter(
      (rel) =>
        rel.source_entity_id === params.id || rel.target_entity_id === params.id,
    );
    return HttpResponse.json({ status: "success", data: incident, meta: meta() });
  }),

  http.get(`${base}/api/v1/graph/entities/:id/neighbors`, ({ params }) => {
    const neighbourIds = new Set<string>();
    for (const rel of sampleRelationships) {
      if (rel.source_entity_id === params.id) {
        neighbourIds.add(rel.target_entity_id);
      } else if (rel.target_entity_id === params.id) {
        neighbourIds.add(rel.source_entity_id);
      }
    }
    const neighbours = sampleEntities.filter((item) =>
      neighbourIds.has(item.id),
    );
    return HttpResponse.json({ status: "success", data: neighbours, meta: meta() });
  }),
];
