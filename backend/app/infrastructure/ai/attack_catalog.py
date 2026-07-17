"""MITRE ATT&CK catalog external knowledge provider (ES-058).

First concrete realization of the provider-neutral
:class:`~app.ai.providers.external.ExternalKnowledgeProvider` port
(rag-architecture §15 "External Retrieval", memory-architecture §4 "External
Knowledge") over a **bundled, curated subset** of the MITRE ATT&CK technique
catalog (``attack_catalog.json``, revisioned; source attribution preserved).
The catalog is packaged reference data, so lookups are deterministic, offline
and CI-able — the baseline external source the live NVD adapter complements.

Lookup semantics: the query is matched against each technique's curated
keyword list (case-insensitive whole-word/phrase matching); techniques with at
least one keyword hit are ranked by hit count (technique id breaks ties,
deterministically) and returned within a fixed result bound. The reported
confidence is a bounded relevance heuristic derived from the hit count —
external knowledge is indicative context, never organizational fact
(rag-architecture §17).

Contract realization (ADR-013): execution is trivially bounded — the catalog
is in memory and no I/O happens per lookup. A malformed or missing bundled
catalog is a packaging defect surfaced eagerly at construction as
:class:`~app.ai.errors.ExternalKnowledgeError`.
"""

import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path

from app.ai.errors import ExternalKnowledgeError
from app.ai.providers.external import (
    ExternalKnowledgeItem,
    ExternalKnowledgeQuery,
)
from app.domain.value_objects import Confidence

logger = logging.getLogger(__name__)

_CATALOG_PATH = Path(__file__).with_name("attack_catalog.json")

# Resource bound on returned techniques per lookup.
_RESULT_LIMIT = 5
# Bounded relevance heuristic: one keyword hit is worth reporting but weak;
# every further hit raises confidence toward (never onto) certainty.
_BASE_CONFIDENCE = 0.4
_CONFIDENCE_PER_HIT = 0.1
_CONFIDENCE_CEILING = 0.9


@dataclass(frozen=True, slots=True)
class _Technique:
    """One curated catalog technique with its precompiled keyword patterns."""

    id: str
    name: str
    tactics: tuple[str, ...]
    description: str
    patterns: tuple[re.Pattern[str], ...]


def _keyword_pattern(keyword: str) -> re.Pattern[str]:
    # Whole-word/phrase match; keywords may carry non-word characters
    # ("cmd.exe", "public-facing"), so the boundaries are word-context
    # lookarounds rather than \b.
    return re.compile(
        rf"(?<!\w){re.escape(keyword)}(?!\w)", re.IGNORECASE
    )


def _parse_catalog(raw: object) -> tuple[str, tuple[_Technique, ...]]:
    """Validate the bundled catalog shape; total — raises on any defect."""

    if not isinstance(raw, dict):
        raise ExternalKnowledgeError(
            "ATT&CK catalog is not a JSON object."
        )
    source = raw.get("source")
    if not isinstance(source, str) or not source.strip():
        raise ExternalKnowledgeError(
            "ATT&CK catalog carries no source label."
        )
    entries = raw.get("techniques")
    if not isinstance(entries, list) or not entries:
        raise ExternalKnowledgeError(
            "ATT&CK catalog carries no techniques."
        )

    techniques: list[_Technique] = []
    for entry in entries:
        if not isinstance(entry, dict):
            raise ExternalKnowledgeError(
                "ATT&CK catalog technique is not an object."
            )
        technique_id = entry.get("id")
        name = entry.get("name")
        description = entry.get("description")
        tactics = entry.get("tactics")
        keywords = entry.get("keywords")
        if (
            not isinstance(technique_id, str)
            or not isinstance(name, str)
            or not isinstance(description, str)
            or not isinstance(tactics, list)
            or not isinstance(keywords, list)
            or not all(isinstance(tactic, str) for tactic in tactics)
            or not all(isinstance(keyword, str) for keyword in keywords)
            or not keywords
        ):
            raise ExternalKnowledgeError(
                "ATT&CK catalog technique has an invalid shape."
            )
        techniques.append(
            _Technique(
                id=technique_id,
                name=name,
                tactics=tuple(tactics),
                description=description,
                patterns=tuple(
                    _keyword_pattern(keyword) for keyword in keywords
                ),
            )
        )
    return source.strip(), tuple(techniques)


class AttackCatalogProvider:
    """``ExternalKnowledgeProvider`` over the bundled ATT&CK subset."""

    def __init__(self, catalog_path: Path = _CATALOG_PATH) -> None:
        # Loaded eagerly: a broken bundled catalog is a packaging defect at
        # composition time, not a per-lookup runtime failure.
        try:
            raw: object = json.loads(catalog_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise ExternalKnowledgeError(
                "ATT&CK catalog could not be loaded "
                f"({type(exc).__name__})."
            ) from exc
        self._source, self._techniques = _parse_catalog(raw)

    async def lookup(
        self, query: ExternalKnowledgeQuery
    ) -> tuple[ExternalKnowledgeItem, ...]:
        """Match the query against the catalog; deterministic, in-memory."""

        scored: list[tuple[int, _Technique]] = []
        for technique in self._techniques:
            hits = sum(
                1
                for pattern in technique.patterns
                if pattern.search(query.query)
            )
            if hits:
                scored.append((hits, technique))
        # Rank by hit count; the technique id breaks ties deterministically.
        scored.sort(key=lambda entry: (-entry[0], entry[1].id))

        items = tuple(
            ExternalKnowledgeItem(
                source=self._source,
                reference=technique.id,
                content=(
                    f"MITRE ATT&CK {technique.id} {technique.name} "
                    f"[{', '.join(technique.tactics)}]: "
                    f"{technique.description}"
                ),
                confidence=Confidence(
                    min(
                        _CONFIDENCE_CEILING,
                        _BASE_CONFIDENCE + _CONFIDENCE_PER_HIT * hits,
                    )
                ),
            )
            for hits, technique in scored[:_RESULT_LIMIT]
        )
        logger.info(
            "attack catalog lookup matched=%s returned=%s",
            len(scored),
            len(items),
        )
        return items
