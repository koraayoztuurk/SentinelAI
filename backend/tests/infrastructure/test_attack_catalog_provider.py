"""Tests for the MITRE ATT&CK catalog external knowledge provider (ES-058).

The bundled, curated catalog realizes the ``ExternalKnowledgeProvider`` port
deterministically (offline, in-memory): case-insensitive whole-word keyword
matching, hit-count ranking with a fixed result bound, bounded relevance
confidence, and eager surfacing of a broken bundled catalog as
``ExternalKnowledgeError``. Plain test functions, ``asyncio.run``.
"""

import asyncio
import json
import tempfile
from pathlib import Path

import pytest

from app.ai.errors import ExternalKnowledgeError
from app.ai.providers.external import (
    ExternalKnowledgeItem,
    ExternalKnowledgeQuery,
)
from app.infrastructure.ai.attack_catalog import AttackCatalogProvider


def _lookup(
    provider: AttackCatalogProvider, query: str
) -> tuple[ExternalKnowledgeItem, ...]:
    return asyncio.run(provider.lookup(ExternalKnowledgeQuery(query=query)))


# ----------------------------------------------------------------- happy path


def test_bundled_catalog_loads_and_matches_by_keyword() -> None:
    provider = AttackCatalogProvider()

    items = _lookup(provider, "Periodic beaconing to a rare external domain")

    references = [item.reference for item in items]
    assert "T1071" in references  # Application Layer Protocol (beaconing)
    item = items[references.index("T1071")]
    assert item.source == "mitre-attack"
    assert item.content.startswith("MITRE ATT&CK T1071")
    assert 0.0 < item.confidence.value <= 0.9


def test_matching_is_case_insensitive() -> None:
    provider = AttackCatalogProvider()

    items = _lookup(provider, "BEACONING detected on HOST-1")

    assert "T1071" in [item.reference for item in items]


def test_matching_requires_whole_words() -> None:
    provider = AttackCatalogProvider()

    # "portscanner" must not match the "port scan" keyword mid-word.
    assert _lookup(provider, "portscanner") == ()
    assert "T1595" in [
        item.reference for item in _lookup(provider, "a port scan was seen")
    ]


def test_unmatched_query_returns_empty() -> None:
    provider = AttackCatalogProvider()

    assert _lookup(provider, "quarterly budget planning meeting") == ()


# ------------------------------------------------------- ranking and bounding


def test_results_are_ranked_by_hit_count_and_bounded() -> None:
    provider = AttackCatalogProvider()

    items = _lookup(
        provider,
        "phishing email with attachment led to powershell execution, "
        "lateral movement over rdp, credential dumping via mimikatz, "
        "ransomware encryption",
    )

    # More matching techniques exist than the result bound allows.
    assert len(items) == 5
    # Two-hit techniques outrank single-hit ones; ties break on technique id.
    assert [item.reference for item in items][:3] == ["T1003", "T1021", "T1566"]


def test_confidence_grows_with_hits_but_stays_bounded() -> None:
    provider = AttackCatalogProvider()

    single = _lookup(provider, "mimikatz")[0]
    double = _lookup(provider, "mimikatz used for credential dumping")[0]

    assert double.reference == single.reference == "T1003"
    assert double.confidence.value > single.confidence.value
    assert double.confidence.value <= 0.9


# -------------------------------------------------------------- broken catalog


def test_malformed_catalog_raises_eagerly() -> None:
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "broken.json"
        path.write_text("not json", encoding="utf-8")

        with pytest.raises(ExternalKnowledgeError):
            AttackCatalogProvider(catalog_path=path)


def test_catalog_with_invalid_technique_shape_raises_eagerly() -> None:
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "invalid.json"
        path.write_text(
            json.dumps(
                {
                    "source": "mitre-attack",
                    "techniques": [{"id": "T0001", "name": "No keywords"}],
                }
            ),
            encoding="utf-8",
        )

        with pytest.raises(ExternalKnowledgeError):
            AttackCatalogProvider(catalog_path=path)


def test_missing_catalog_file_raises_eagerly() -> None:
    with pytest.raises(ExternalKnowledgeError):
        AttackCatalogProvider(catalog_path=Path("does-not-exist.json"))
