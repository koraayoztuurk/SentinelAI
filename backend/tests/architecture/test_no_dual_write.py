"""AC-14 — no request path writes to more than one store (ES-069).

Part of the ES-033 architecture-test family (static ``ast`` analysis of
``app/``, no imports, standard library only), split into its own module because
the check is a small analysis rather than a single import rule.

**The constraint.** A service operation writes at most one store; derived
representations reach their store through the owning service's transactional
outbox (ADR-012). Until now this held *by construction* and was verified by
review — the debt this closes.

**How it is checked.** For every class in the application layer that holds
persistence ports:

1. each constructor port is mapped to the store family its adapter belongs to
   (the registry below — deliberately explicit, and asserted complete, so a new
   port cannot silently escape the check);
2. a port method is a **write** when the port declares it returning ``None`` —
   commands return nothing, queries return something. Derived from the port
   declarations themselves rather than from a hand-maintained list of verbs, so
   a new write operation is covered the day it is declared;
3. writes are attributed per method, then propagated through the class's own
   internal calls, so a write hidden in a private helper still counts against
   the public operation that reaches it;
4. every public operation must write **at most one** store family.

**The exemption is a classification, not a hole.** The outbox projections write
two stores by design — that is precisely the mechanism ADR-012 prescribes, and
the reason request paths never have to. They are named explicitly below, so a
newly added class is checked by default and can only become exempt by someone
deciding it is a projection.
"""

import ast
from pathlib import Path

import pytest

import app

_APP_ROOT = Path(app.__file__).resolve().parent
_APPLICATION_ROOT = _APP_ROOT / "application"

# Store family per persistence port. The application layer is store-agnostic by
# design (it holds ports, not adapters), so the binding lives here — the one
# place that has to know which technology backs each port to reason about
# dual writes at all.
_STORE_FAMILY_BY_PORT: dict[str, str] = {
    "InvestigationRepository": "postgres",
    "EvidenceRepository": "postgres",
    "FindingRepository": "postgres",
    "ReportRepository": "postgres",
    "OutcomeRepository": "postgres",
    "TraceRepository": "postgres",
    "MemoryRepository": "postgres",
    # The outbox is a PostgreSQL table written in the *same* transaction as the
    # business row — that is what makes ADR-012 a transactional outbox rather
    # than a dual write.
    "OutboxRepository": "postgres",
    "GraphRepository": "neo4j",
    "MemoryVectorStore": "qdrant",
    "EvidencePayloadStore": "object_store",
}

# Classes whose job *is* to move data between stores (ADR-012). Naming them
# keeps the exemption a decision on the record.
_OUTBOX_PROJECTIONS = frozenset(
    {
        "MemoryEmbeddingProjector",
        "EvidencePayloadErasureProjector",
    }
)

# Annotations shaped like a persistence port. Anything matching must appear in
# the family registry; anything else (an embedder, a retry policy, a clock) is
# not a store and is ignored.
_PORT_SUFFIXES = ("Repository", "Store")


def _application_files() -> list[Path]:
    return [
        path
        for path in sorted(_APPLICATION_ROOT.rglob("*.py"))
        if "__pycache__" not in path.parts
    ]


def _base_type(annotation: ast.expr) -> str:
    """Return the annotation's type name, unwrapping an optional."""

    text = ast.unparse(annotation)
    return text.removesuffix(" | None").strip()


def _looks_like_port(type_name: str) -> bool:
    return type_name.endswith(_PORT_SUFFIXES)


def _port_write_methods(trees: list[ast.Module]) -> dict[str, set[str]]:
    """Return each port's command methods — those declared returning ``None``."""

    commands: dict[str, set[str]] = {}
    for tree in trees:
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            if node.name not in _STORE_FAMILY_BY_PORT:
                continue
            names = {
                member.name
                for member in node.body
                if isinstance(member, ast.AsyncFunctionDef | ast.FunctionDef)
                and member.returns is not None
                and ast.unparse(member.returns) == "None"
            }
            commands.setdefault(node.name, set()).update(names)
    return commands


def _held_ports(class_def: ast.ClassDef) -> dict[str, str]:
    """Map ``self`` attribute -> port type, for the ports a class is given.

    Reads the constructor's annotations and the assignments that store them, so
    the attribute a method actually calls can be traced back to its port.
    """

    init = next(
        (
            member
            for member in class_def.body
            if isinstance(member, ast.AsyncFunctionDef | ast.FunctionDef)
            and member.name == "__init__"
        ),
        None,
    )
    if init is None:
        return {}

    arguments = init.args.args[1:] + init.args.kwonlyargs
    port_by_parameter = {
        argument.arg: _base_type(argument.annotation)
        for argument in arguments
        if argument.annotation is not None
        and _looks_like_port(_base_type(argument.annotation))
    }

    ports: dict[str, str] = {}
    for node in ast.walk(init):
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target, value = node.targets[0], node.value
        if (
            isinstance(target, ast.Attribute)
            and isinstance(target.value, ast.Name)
            and target.value.id == "self"
            and isinstance(value, ast.Name)
            and value.id in port_by_parameter
        ):
            ports[target.attr] = port_by_parameter[value.id]
    return ports


def _self_attribute_call(node: ast.Call) -> tuple[str, str] | None:
    """Return ``(attribute, method)`` for a ``self._x.y(...)`` call."""

    if not isinstance(node.func, ast.Attribute):
        return None
    receiver = node.func.value
    if (
        isinstance(receiver, ast.Attribute)
        and isinstance(receiver.value, ast.Name)
        and receiver.value.id == "self"
    ):
        return receiver.attr, node.func.attr
    return None


def _self_method_call(node: ast.Call) -> str | None:
    """Return the method name for a ``self.y(...)`` call on the class itself."""

    if (
        isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "self"
    ):
        return node.func.attr
    return None


def _written_families(
    class_def: ast.ClassDef, port_commands: dict[str, set[str]]
) -> dict[str, set[str]]:
    """Return the store families each method of the class writes.

    Writes performed by a private helper are propagated to every method that
    reaches it, so the result is what an *operation* writes, not what its
    outermost function body happens to contain.
    """

    ports = _held_ports(class_def)
    direct: dict[str, set[str]] = {}
    internal_calls: dict[str, set[str]] = {}

    for member in class_def.body:
        if not isinstance(member, ast.AsyncFunctionDef | ast.FunctionDef):
            continue
        families: set[str] = set()
        callees: set[str] = set()
        for node in ast.walk(member):
            if not isinstance(node, ast.Call):
                continue
            call = _self_attribute_call(node)
            if call is not None:
                attribute, method = call
                port = ports.get(attribute)
                if port is not None and method in port_commands.get(port, set()):
                    families.add(_STORE_FAMILY_BY_PORT[port])
                continue
            callee = _self_method_call(node)
            if callee is not None:
                callees.add(callee)
        direct[member.name] = families
        internal_calls[member.name] = callees

    # Fixed point over the class's internal call graph (it is tiny, and this
    # terminates even if two helpers call each other).
    resolved = {name: set(families) for name, families in direct.items()}
    changed = True
    while changed:
        changed = False
        for name, callees in internal_calls.items():
            for callee in callees:
                reachable = resolved.get(callee)
                if reachable and not reachable <= resolved[name]:
                    resolved[name] |= reachable
                    changed = True
    return resolved


def _dual_write_violations(trees: list[ast.Module]) -> list[tuple[str, str, set[str]]]:
    """Return ``(class, operation, families)`` for every multi-store operation."""

    port_commands = _port_write_methods(trees)
    violations: list[tuple[str, str, set[str]]] = []
    for tree in trees:
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            if node.name in _OUTBOX_PROJECTIONS:
                continue
            if not _held_ports(node):
                continue
            for method, families in _written_families(node, port_commands).items():
                if method.startswith("_"):
                    continue  # reported through the operation that reaches it
                if len(families) > 1:
                    violations.append((node.name, method, families))
    return violations


def _application_trees() -> list[ast.Module]:
    return [
        ast.parse(path.read_text(encoding="utf-8"))
        for path in _application_files()
    ]


def _port_holding_classes(trees: list[ast.Module]) -> dict[str, dict[str, str]]:
    holders: dict[str, dict[str, str]] = {}
    for tree in trees:
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                ports = _held_ports(node)
                if ports:
                    holders[node.name] = ports
    return holders


# ----------------------------------------------------------------- the constraint


@pytest.mark.architecture
def test_no_service_operation_writes_two_stores() -> None:
    # AC-14: one operation, one store. Cross-store propagation is the outbox's
    # job, never an operation's.
    violations = _dual_write_violations(_application_trees())
    assert not violations, f"operations writing more than one store: {violations}"


# ------------------------------------------------------- the check cannot go stale


@pytest.mark.architecture
def test_every_persistence_port_is_assigned_a_store_family() -> None:
    # A port missing from the registry would be invisible to the check, so a
    # new one must be classified before it can be used.
    unclassified = {
        port
        for ports in _port_holding_classes(_application_trees()).values()
        for port in ports.values()
        if port not in _STORE_FAMILY_BY_PORT
    }
    assert not unclassified, f"persistence ports with no store family: {unclassified}"


@pytest.mark.architecture
def test_the_outbox_projection_exemption_is_not_stale() -> None:
    # An exemption for a class that no longer exists would quietly widen the
    # hole the next time that name is reused.
    holders = set(_port_holding_classes(_application_trees()))
    missing = _OUTBOX_PROJECTIONS - holders
    assert not missing, f"exempted classes that no longer hold ports: {missing}"


@pytest.mark.architecture
def test_the_check_detects_a_dual_write() -> None:
    # The negative control: without it, a check that silently stopped finding
    # anything would look exactly like a passing constraint.
    synthetic = ast.parse(
        '''
class SmugglingService:
    def __init__(
        self, memory: MemoryRepository, vectors: MemoryVectorStore
    ) -> None:
        self._memory = memory
        self._vectors = vectors

    async def create(self, item: object) -> None:
        await self._memory.add(item)
        await self._store_vector(item)

    async def _store_vector(self, item: object) -> None:
        await self._vectors.upsert(item)
'''
    )

    violations = _dual_write_violations(_application_trees() + [synthetic])

    assert violations == [
        ("SmugglingService", "create", {"postgres", "qdrant"})
    ]
