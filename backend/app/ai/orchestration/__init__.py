"""AI orchestration compositions (ADR-010, ADR-013).

The AI Runtime owns the compositions that connect agents to executors: the
Investigation Loop (Planner decision loop) and the Retrieval Flow (Memory Agent
→ RAG Pipeline). Both run agents through the Agent Runtime (the single
execution path), record their steps into the Investigation Trace, and remain
stateless; identifiers, timestamps and state assembly are caller-supplied
through replaceable ports.
"""

from app.ai.orchestration.loop import (
    ActionExecutor,
    ActionIdSource,
    InvestigationLoop,
    LoopEnd,
    LoopOutcome,
    StateAssembler,
)
from app.ai.orchestration.retrieval import RetrievalFlow
from app.ai.orchestration.tracing import Clock, IdSource, TraceSink

__all__ = [
    "ActionExecutor",
    "ActionIdSource",
    "Clock",
    "IdSource",
    "InvestigationLoop",
    "LoopEnd",
    "LoopOutcome",
    "StateAssembler",
    "RetrievalFlow",
    "TraceSink",
]
