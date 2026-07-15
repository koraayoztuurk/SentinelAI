"""Tests for the concrete Investigation State assembler (ES-044).

The assembler realizes the Workspace / Context Builder responsibility
(planner-agent §4) over the Investigation Service: objectives derive from the
title, confidence from the strongest finding, history from the most recent
trace entries. In-memory doubles, plain functions, ``asyncio.run``.
"""

import asyncio

from app.ai.orchestration.assembler import InvestigationStateAssembler
from app.application.investigation import InvestigationService
from app.application.planner.actions import (
    ControlAction,
    ControlKind,
    ExecutionResult,
    ExecutionStatus,
)
from app.domain.identifiers import InvestigationId, TraceEntryId
from app.domain.trace import TraceEntry, TraceEntryKind
from app.domain.value_objects import ActorRef
from tests.support.builders import (
    FIXED_TIME,
    build_evidence,
    build_finding,
    build_investigation,
    make_investigation_service,
)


def _entry(service_entry_id: str, summary: str) -> TraceEntry:
    return TraceEntry(
        id=TraceEntryId(service_entry_id),
        investigation_id=InvestigationId("inv-1"),
        kind=TraceEntryKind.PLANNER_DECISION,
        actor=ActorRef("planner-agent"),
        summary=summary,
        reference="act-1",
        created_at=FIXED_TIME,
    )


async def _populated_service() -> InvestigationService:
    service = make_investigation_service()
    await service.create(build_investigation("inv-1", title="Lateral movement"))
    await service.attach_evidence(build_evidence("ev-1", "inv-1"))
    await service.attach_evidence(build_evidence("ev-2", "inv-1"))
    await service.create_finding(
        build_finding(
            "f-1", "inv-1", supporting_evidence=("ev-1",), confidence=0.4
        )
    )
    await service.create_finding(
        build_finding(
            "f-2", "inv-1", supporting_evidence=("ev-2",), confidence=0.9
        )
    )
    return service


def test_assemble_builds_state_from_service_data() -> None:
    async def scenario() -> None:
        service = await _populated_service()
        assembler = InvestigationStateAssembler(service)

        state = await assembler.assemble(InvestigationId("inv-1"))

        assert state.investigation_id == InvestigationId("inv-1")
        assert state.status == "created"
        # A single objective derived from the investigation title.
        assert state.objectives == ("Investigate: Lateral movement",)
        # Confidence reflects the strongest finding.
        assert state.confidence.value == 0.9
        assert [e.value for e in state.evidence_ids] == ["ev-1", "ev-2"]
        assert [f.value for f in state.finding_ids] == ["f-1", "f-2"]
        assert state.history == ()
        assert state.pending_tasks == ()

    asyncio.run(scenario())


def test_confidence_is_zero_without_findings() -> None:
    async def scenario() -> None:
        service = make_investigation_service()
        await service.create(build_investigation("inv-1"))
        state = await InvestigationStateAssembler(service).assemble(
            InvestigationId("inv-1")
        )
        assert state.confidence.value == 0.0

    asyncio.run(scenario())


def test_history_carries_recent_trace_entries_bounded() -> None:
    async def scenario() -> None:
        service = make_investigation_service()
        await service.create(build_investigation("inv-1"))
        for index in range(12):
            await service.record_trace(_entry(f"t-{index}", f"step {index}"))

        state = await InvestigationStateAssembler(service).assemble(
            InvestigationId("inv-1")
        )

        # Bounded to the most recent entries, chronological, kind-prefixed.
        assert len(state.history) == 10
        assert state.history[0] == "planner_decision: step 2"
        assert state.history[-1] == "planner_decision: step 11"

    asyncio.run(scenario())


def test_next_state_reassembles_the_current_snapshot() -> None:
    async def scenario() -> None:
        service = await _populated_service()
        assembler = InvestigationStateAssembler(service)
        first = await assembler.assemble(InvestigationId("inv-1"))

        # New data arrives between cycles; the loop's observation reflects it.
        await service.attach_evidence(build_evidence("ev-3", "inv-1"))
        result = ExecutionResult(
            action_id="act-1",
            target=None,
            status=ExecutionStatus.COMPLETED,
            value=ControlAction(action_id="act-1", kind=ControlKind.COMPLETE),
        )
        second = await assembler.next_state(first, result)

        assert [e.value for e in second.evidence_ids] == [
            "ev-1",
            "ev-2",
            "ev-3",
        ]

    asyncio.run(scenario())


def test_next_state_preserves_retrieved_knowledge_across_cycles() -> None:
    async def scenario() -> None:
        from dataclasses import replace

        service = await _populated_service()
        assembler = InvestigationStateAssembler(service)
        first = await assembler.assemble(InvestigationId("inv-1"))
        enriched = replace(
            first, knowledge=("[semantic] memory:m-1 (confidence=0.90) x",)
        )

        result = ExecutionResult(
            action_id="act-1",
            target=None,
            status=ExecutionStatus.COMPLETED,
            value=ControlAction(action_id="act-1", kind=ControlKind.COMPLETE),
        )
        second = await assembler.next_state(enriched, result)

        # The run's retrieval context stays observable to the agent (ES-051)
        # while the rest of the state reflects the persisted reality.
        assert second.knowledge == enriched.knowledge

    asyncio.run(scenario())
