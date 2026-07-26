"""Governance conformance (AC-16, ADR-020 — ES-071).

The architecture corpus is this project's primary artifact, and until now exactly
one of its derivable properties was mechanically kept true: the committed API
contract (AC-15). Everything else relied on review discipline and drifted — two
documents whose front matter had fallen behind their own version history, one
with its history rows out of order, one with no history at all, an RFC directory
with no index, and configuration fields the platform reads but the configuration
example never mentioned.

These checks generalize the AC-15 pattern to the remaining derivable governance
properties. They verify that governance artifacts are **consistent and
complete** — never that they are *correct*: accuracy and clarity stay a review
responsibility (ADR-020 §5). A check that could fire on a judgement call does
not belong here, because a constraint that cries wolf stops being enforced.

Marked ``architecture`` (Architecture Validation, testing-strategy §5): AC-16
lives in the Architecture Testing constraint catalogue like every other AC.
"""

import importlib
import json
import pkgutil
import re
from pathlib import Path

import pytest
from pydantic_settings import BaseSettings

import app.config

_REPO_ROOT = Path(__file__).resolve().parents[2].parent
_DOCS = _REPO_ROOT / "docs"
_DECISIONS = _DOCS / "09-decisions"
_PROPOSALS = _DOCS / "10-rfc"

# ADR-020 §1: the ADR vocabulary without ``Proposed`` — a document is not a
# proposal (that is what an RFC is for).
_DOCUMENT_STATUSES = {"Draft", "Accepted", "Superseded", "Deprecated"}
_DECISION_STATUSES = {"Proposed", "Accepted", "Rejected", "Superseded", "Deprecated"}

_FRONT_MATTER = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)
_VERSION_ROW = re.compile(
    r"^\| (\d+\.\d+\.\d+) \| (\d{4}-\d{2}-\d{2}) \|", re.MULTILINE
)
_SEMVER = re.compile(r"\A\d+\.\d+\.\d+\Z")
_ISO_DATE = re.compile(r"\A\d{4}-\d{2}-\d{2}\Z")
_CONSTRAINT_ROW = re.compile(r"^\| (AC-\d+) \|(.*)$", re.MULTILINE)
_ENFORCED_PATH = re.compile(r"Enforced \(`([^`]+)`\)")
_REFERENCE = re.compile(r"\b(ADR|RFC)-(\d{3})\b")
_ENV_ASSIGNMENT = re.compile(r"^#?\s*([A-Z][A-Z0-9_]*)=", re.MULTILINE)

pytestmark = pytest.mark.architecture


def _front_matter(path: Path) -> dict[str, str]:
    match = _FRONT_MATTER.match(path.read_text(encoding="utf-8"))
    if match is None:
        return {}
    fields: dict[str, str] = {}
    for line in match.group(1).splitlines():
        key, separator, value = line.partition(":")
        if separator:
            fields[key.strip()] = value.strip()
    return fields


def _architecture_documents() -> list[Path]:
    """Every document governed by the ADR-020 lifecycle.

    Decision and proposal files carry their own front-matter shape and status
    vocabulary; the RFC template is a form, not a proposal.
    """

    return [
        path
        for path in sorted(_DOCS.rglob("*.md"))
        if not path.name.startswith(("ADR-", "RFC-"))
    ]


def _decision_documents() -> list[Path]:
    return sorted(_DECISIONS.glob("ADR-*.md"))


def _proposal_documents() -> list[Path]:
    return [
        path
        for path in sorted(_PROPOSALS.glob("RFC-*.md"))
        if path.name != "RFC-000-template.md"
    ]


def _identifier(path: Path) -> str:
    return path.name.split("-", 2)[0] + "-" + path.name.split("-", 2)[1]


def _configured_environment_variables() -> set[str]:
    """Every environment variable the platform's settings classes read."""

    names: set[str] = set()
    for module_info in pkgutil.iter_modules(app.config.__path__):
        module = importlib.import_module(f"app.config.{module_info.name}")
        for member in vars(module).values():
            if (
                isinstance(member, type)
                and issubclass(member, BaseSettings)
                and member is not BaseSettings
                and member.__module__ == module.__name__
            ):
                prefix = member.model_config.get("env_prefix") or ""
                names.update(
                    f"{prefix}{field}".upper() for field in member.model_fields
                )
    return names


def test_every_architecture_document_declares_valid_front_matter() -> None:
    problems: list[str] = []
    for path in _architecture_documents():
        relative = path.relative_to(_REPO_ROOT).as_posix()
        fields = _front_matter(path)
        if not fields:
            problems.append(f"{relative}: no front matter")
            continue
        for key in ("title", "version", "status", "owner", "last_updated"):
            if key not in fields:
                problems.append(f"{relative}: front matter is missing `{key}`")
        if not _SEMVER.match(fields.get("version", "")):
            problems.append(
                f"{relative}: version `{fields.get('version')}` is not semver"
            )
        if fields.get("status") not in _DOCUMENT_STATUSES:
            problems.append(
                f"{relative}: status `{fields.get('status')}` is not one of "
                f"{sorted(_DOCUMENT_STATUSES)} (ADR-020 §1)"
            )
        if not _ISO_DATE.match(fields.get("last_updated", "")):
            problems.append(f"{relative}: last_updated is not an ISO date")
    assert not problems, "Document front matter (ADR-020 §1):\n" + "\n".join(problems)


def test_document_front_matter_matches_its_own_version_history() -> None:
    problems: list[str] = []
    for path in _architecture_documents():
        relative = path.relative_to(_REPO_ROOT).as_posix()
        fields = _front_matter(path)
        rows = _VERSION_ROW.findall(path.read_text(encoding="utf-8"))
        if not rows:
            problems.append(f"{relative}: no Version History")
            continue
        versions = [
            tuple(int(part) for part in version.split(".")) for version, _ in rows
        ]
        if versions != sorted(versions):
            problems.append(
                f"{relative}: Version History rows are not in ascending order"
            )
        latest_version, latest_date = rows[versions.index(max(versions))]
        if fields.get("version") != latest_version:
            problems.append(
                f"{relative}: front matter version {fields.get('version')} but the "
                f"history reaches {latest_version}"
            )
        if fields.get("last_updated") != latest_date:
            problems.append(
                f"{relative}: front matter last_updated {fields.get('last_updated')} "
                f"but the latest history entry is dated {latest_date}"
            )
    assert not problems, "Version history consistency (AC-16):\n" + "\n".join(problems)


def test_decision_and_proposal_front_matter_declares_a_known_status() -> None:
    problems: list[str] = []
    for path in _decision_documents() + _proposal_documents():
        relative = path.relative_to(_REPO_ROOT).as_posix()
        fields = _front_matter(path)
        if fields.get("status") not in _DECISION_STATUSES:
            problems.append(f"{relative}: status `{fields.get('status')}`")
        if not _ISO_DATE.match(fields.get("date", "")):
            problems.append(
                f"{relative}: date `{fields.get('date')}` is not an ISO date"
            )
    assert not problems, "Decision/proposal front matter:\n" + "\n".join(problems)


def test_decision_and_proposal_indexes_are_complete() -> None:
    """Both directions: nothing unindexed, nothing indexed that does not exist."""

    problems: list[str] = []
    for files, index_path, label in (
        (_decision_documents(), _DECISIONS / "README.md", "ADR"),
        (_proposal_documents(), _PROPOSALS / "README.md", "RFC"),
    ):
        index = index_path.read_text(encoding="utf-8")
        listed = {
            f"{kind}-{number}"
            for kind, number in _REFERENCE.findall(index)
            if kind == label
        } - {"RFC-000"}  # the single-page form, named in the index as a form
        present = {_identifier(path) for path in files}
        for missing in sorted(present - listed):
            problems.append(
                f"{missing} exists but is not listed in "
                f"{index_path.relative_to(_REPO_ROOT).as_posix()}"
            )
        for dangling in sorted(listed - present):
            problems.append(
                f"{dangling} is listed in "
                f"{index_path.relative_to(_REPO_ROOT).as_posix()} but has no file"
            )
    assert not problems, "Index completeness (ADR-020 §4):\n" + "\n".join(problems)


def test_every_referenced_decision_and_proposal_exists() -> None:
    known = {
        _identifier(path) for path in _decision_documents() + _proposal_documents()
    }
    known.add("RFC-000")  # the single-page form itself
    problems: list[str] = []
    for path in sorted(_DOCS.rglob("*.md")):
        referenced = {
            f"{kind}-{number}"
            for kind, number in _REFERENCE.findall(path.read_text(encoding="utf-8"))
        }
        for dangling in sorted(referenced - known):
            problems.append(
                f"{path.relative_to(_REPO_ROOT).as_posix()} references {dangling}"
            )
    assert not problems, "Dangling governance references:\n" + "\n".join(problems)


def test_enforced_constraints_name_a_verification_that_exists() -> None:
    """The catalogue may not claim enforcement it does not have."""

    catalogue = (_DOCS / "08-testing" / "architecture-testing.md").read_text(
        encoding="utf-8"
    )
    enforced = [
        (constraint, _ENFORCED_PATH.search(row))
        for constraint, row in _CONSTRAINT_ROW.findall(catalogue)
    ]
    claimed = [
        (constraint, match.group(1))
        for constraint, match in enforced
        if match is not None
    ]
    assert claimed, "No enforced constraint found in the catalogue — parsing is broken."
    problems = [
        f"{constraint} claims enforcement by `{location}`, which does not exist"
        for constraint, location in claimed
        if not (_REPO_ROOT / location).exists()
    ]
    assert not problems, "Constraint catalogue (AC-16):\n" + "\n".join(problems)


def test_configuration_example_documents_every_setting() -> None:
    """Every field the settings classes read appears in ``.env.example``.

    One direction only: the example legitimately documents variables that are
    *not* settings fields — secrets are resolved through the SecretProvider from
    the process environment, never through a settings class.
    """

    documented = set(
        _ENV_ASSIGNMENT.findall(
            (_REPO_ROOT / ".env.example").read_text(encoding="utf-8")
        )
    )
    undocumented = sorted(_configured_environment_variables() - documented)
    assert not undocumented, (
        "Configuration fields the platform reads but `.env.example` never mentions "
        f"(configuration-management, AC-16): {undocumented}"
    )


def test_deployment_units_declare_the_same_platform_version() -> None:
    """One platform, one version (release-management §4a, ADR-021 §1).

    The units are not independently versionable — the frontend speaks exactly
    one API contract and both are published from the same commit — so a
    disagreement here is a release-identity defect, not a difference of opinion.
    The third declaration, the release tag, is verified by CI: it is not in the
    tree, so no test can read it.
    """

    backend_manifest = (_REPO_ROOT / "backend" / "pyproject.toml").read_text(
        encoding="utf-8"
    )
    backend = re.search(r'^version = "([^"]+)"', backend_manifest, re.MULTILINE)
    assert backend is not None, "backend/pyproject.toml declares no version"

    frontend_manifest = json.loads(
        (_REPO_ROOT / "frontend" / "package.json").read_text(encoding="utf-8")
    )
    declared = {
        "backend/pyproject.toml": backend.group(1),
        "frontend/package.json": frontend_manifest["version"],
    }
    assert len(set(declared.values())) == 1, (
        "The deployment units declare different platform versions "
        f"(ADR-021 §1): {declared}"
    )
