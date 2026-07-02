"""Architecture tests (ES-033).

Independently verify that the backend implementation preserves the Clean
Architecture boundaries and the platform's Permanent Engineering Decisions
(architecture-testing.md — Boundary / Ownership / Constraint validation). The checks
are static: each source file under ``app/`` is parsed with ``ast`` and its imports
(and clock usage) are inspected. No modules are imported to run the checks, and no
framework beyond the standard library is used.

Marked ``architecture`` (Architecture Validation, testing-strategy §5).
"""

import ast
from pathlib import Path

import pytest

import app

_APP_ROOT = Path(app.__file__).resolve().parent
_BACKEND_ROOT = _APP_ROOT.parent


def _module_name(path: Path) -> str:
    parts = list(path.relative_to(_BACKEND_ROOT).with_suffix("").parts)
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _package_files(package: str) -> list[Path]:
    package_dir = _BACKEND_ROOT.joinpath(*package.split("."))
    return [
        path
        for path in sorted(package_dir.rglob("*.py"))
        if "__pycache__" not in path.parts
    ]


def _imported_app_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("app"):
                    imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            # The codebase uses absolute imports only (verified); level 0.
            if node.level == 0 and node.module and node.module.startswith("app"):
                imports.add(node.module)
    return imports


def _forbidden_import_violations(
    package: str, forbidden: tuple[str, ...]
) -> list[tuple[str, str]]:
    violations: list[tuple[str, str]] = []
    for path in _package_files(package):
        module = _module_name(path)
        for imported in sorted(_imported_app_modules(path)):
            if any(
                imported == prefix or imported.startswith(prefix + ".")
                for prefix in forbidden
            ):
                violations.append((module, imported))
    return violations


def _stdlib_import_violations(
    package: str, modules: set[str]
) -> list[tuple[str, str]]:
    violations: list[tuple[str, str]] = []
    for path in _package_files(package):
        module = _module_name(path)
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split(".")[0] in modules:
                        violations.append((module, alias.name))
            elif isinstance(node, ast.ImportFrom):
                if node.level == 0 and node.module in modules:
                    violations.append((module, node.module))
    return violations


def _root_name(node: ast.expr) -> str | None:
    while isinstance(node, ast.Attribute):
        node = node.value
    return node.id if isinstance(node, ast.Name) else None


def _clock_call_violations(package: str) -> list[tuple[str, str]]:
    violations: list[tuple[str, str]] = []
    for path in _package_files(package):
        module = _module_name(path)
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr in {"now", "utcnow"}
                and _root_name(node.func.value) == "datetime"
            ):
                violations.append((module, node.func.attr))
    return violations


# ------------------------------------------------------------- boundary validation


@pytest.mark.architecture
def test_domain_depends_only_on_domain_and_shared_kernel() -> None:
    # The domain is technology-independent: it may reference only the domain itself
    # and the shared kernel (the base exception hierarchy).
    violations = _forbidden_import_violations(
        "app.domain",
        (
            "app.application",
            "app.infrastructure",
            "app.presentation",
            "app.ai",
            "app.core",
            "app.config",
            "app.observability",
            "app.dependencies",
        ),
    )
    assert not violations, f"domain crossed a boundary: {violations}"


@pytest.mark.architecture
def test_application_does_not_depend_on_infrastructure_or_presentation() -> None:
    violations = _forbidden_import_violations(
        "app.application", ("app.infrastructure", "app.presentation")
    )
    assert not violations, f"application crossed a boundary: {violations}"


@pytest.mark.architecture
def test_ai_runtime_does_not_depend_on_infrastructure_or_presentation() -> None:
    # The AI Runtime never accesses persistence directly and is not a web layer.
    violations = _forbidden_import_violations(
        "app.ai", ("app.infrastructure", "app.presentation")
    )
    assert not violations, f"AI runtime crossed a boundary: {violations}"


@pytest.mark.architecture
def test_presentation_does_not_import_infrastructure_directly() -> None:
    violations = _forbidden_import_violations(
        "app.presentation", ("app.infrastructure",)
    )
    assert not violations, f"presentation reached into infrastructure: {violations}"


@pytest.mark.architecture
def test_shared_kernel_has_no_dependency_on_app() -> None:
    # The shared kernel is the base; it must not depend on any other app package.
    violations = _forbidden_import_violations(
        "app.shared",
        ("app.domain", "app.application", "app.infrastructure", "app.presentation",
         "app.ai", "app.core", "app.config", "app.observability", "app.dependencies"),
    )
    assert not violations, f"shared kernel gained an app dependency: {violations}"


# ----------------------------------------------------------- constraint validation


@pytest.mark.architecture
def test_domain_and_services_generate_no_identifiers() -> None:
    # Caller supplies identifiers — no UUID generation inside the domain or services.
    assert not _stdlib_import_violations("app.domain", {"uuid"})
    assert not _stdlib_import_violations("app.application", {"uuid"})


@pytest.mark.architecture
def test_domain_and_services_read_no_clock() -> None:
    # Caller supplies timestamps — no datetime.now()/utcnow() in domain or services.
    assert not _clock_call_violations("app.domain")
    assert not _clock_call_violations("app.application")
