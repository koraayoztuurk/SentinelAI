// Sample investigation data for the mocked Backend API (dev + tests only).
//
// The concrete persistence binding is deferred on the backend (ES-005), so MSW
// serves representative data shaped exactly like the real API responses. This is
// never bundled into the production build.

import type { FindingDto, InvestigationDto } from "../communication/investigations";

export const SAMPLE_INVESTIGATION_ID = "inv-001";

export const sampleInvestigation: InvestigationDto = {
  id: SAMPLE_INVESTIGATION_ID,
  title: "Suspicious lateral movement on finance subnet",
  status: "active",
  created_at: "2026-06-28T09:15:00Z",
  owner: "analyst-erin",
  priority: "high",
};

export const sampleFindings: readonly FindingDto[] = [
  {
    id: "fnd-001",
    investigation_id: SAMPLE_INVESTIGATION_ID,
    supporting_evidence: ["ev-101", "ev-102"],
    creator: "graph-analysis-agent",
    created_at: "2026-06-28T10:05:00Z",
    confidence: 0.86,
    status: "validated",
    related_entities: ["host-12", "host-19"],
    related_relationships: ["rel-7"],
  },
  {
    id: "fnd-002",
    investigation_id: SAMPLE_INVESTIGATION_ID,
    supporting_evidence: ["ev-110"],
    creator: "analyst-erin",
    created_at: "2026-06-28T11:40:00Z",
    confidence: 0.93,
    status: "accepted",
    related_entities: ["user-jdoe"],
    related_relationships: [],
  },
  {
    id: "fnd-003",
    investigation_id: SAMPLE_INVESTIGATION_ID,
    supporting_evidence: ["ev-120"],
    creator: "threat-intel-agent",
    created_at: "2026-06-28T12:10:00Z",
    confidence: 0.41,
    status: "proposed",
    related_entities: [],
    related_relationships: [],
  },
];
