"""NVD CVE external knowledge provider adapter (ES-058).

Live realization of the provider-neutral
:class:`~app.ai.providers.external.ExternalKnowledgeProvider` port over the
NVD (National Vulnerability Database) REST API 2.0 via ``httpx`` (no vendor
SDK — one endpoint, one JSON shape, explicit error mapping; the ES-054
adapter pattern). It answers the documented "CVE databases" external source
(rag-architecture §15, memory-architecture §4).

Lookup semantics: an explicit CVE identifier in the query resolves directly
(``cveId``); otherwise the query text runs as a bounded ``keywordSearch``.
NVD's keyword search requires every term to match, so prose queries often
return zero items — an empty result is a truthful answer, never an error.
NVD reports no relevance measure, so items carry a fixed neutral confidence:
external knowledge stays visible but never dominant (rag-architecture §17).

Contract realization (ADR-013), mirroring the NVIDIA adapter (ES-054):

- **Bounded execution time** — every call runs under ``asyncio.timeout`` with
  the configured bound (httpx gets the same value as its network timeout).
- **Total error mapping** — transport failures, non-success HTTP statuses
  (rate limits included) and malformed payloads all map to
  ``ExternalKnowledgeError`` with a bounded, key-free message; a malformed
  *item* inside an otherwise valid payload is skipped, not fatal.
- **Key hygiene** — ``NVD_API_KEY`` is **optional by NVD's own contract**
  (keyless access is rate-limited harder): it is consumed through the
  ``SecretProvider`` when present and the adapter degrades to keyless access
  otherwise (deliberate deviation from the LLM adapters' mandatory-key
  stance). When present, the key travels only as the ``apiKey`` header —
  never in the URL, never in errors or logs.
"""

import asyncio
import logging
import re

import httpx

from app.ai.errors import ExternalKnowledgeError
from app.ai.providers.external import (
    ExternalKnowledgeItem,
    ExternalKnowledgeQuery,
)
from app.application.secrets import (
    SecretName,
    SecretNotFoundError,
    SecretProvider,
)
from app.config.ai import NvdSettings
from app.domain.value_objects import Confidence
from app.shared.secret import Secret

logger = logging.getLogger(__name__)

NVD_API_KEY = SecretName("NVD_API_KEY")

_BASE_URL = "https://services.nvd.nist.gov/rest/json/cves/2.0"
_SOURCE = "nvd"
_CVE_ID = re.compile(r"\bCVE-\d{4}-\d{4,}\b", re.IGNORECASE)
# Bound on the keyword query sent out (objectives can be long prose).
_QUERY_LIMIT = 256
# Bound on provider-supplied text quoted into error messages.
_ERROR_DETAIL_LIMIT = 200
# Bound on each item's description carried into the context.
_CONTENT_LIMIT = 500
# NVD reports no relevance measure (see module docstring).
_NEUTRAL_CONFIDENCE = Confidence(0.5)


class NvdCveProvider:
    """``ExternalKnowledgeProvider`` adapter over the NVD CVE API 2.0."""

    def __init__(
        self,
        settings: NvdSettings,
        secrets: SecretProvider,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._settings = settings
        # The key is optional (NVD contract): resolved eagerly when present,
        # keyless access otherwise — never a configuration error.
        self._api_key: Secret | None
        try:
            self._api_key = secrets.resolve(NVD_API_KEY)
        except SecretNotFoundError:
            self._api_key = None
        # Injectable transport keeps the contract tests deterministic
        # (httpx.MockTransport); None means the real network.
        self._transport = transport

    async def lookup(
        self, query: ExternalKnowledgeQuery
    ) -> tuple[ExternalKnowledgeItem, ...]:
        """Look up CVEs for the query within the configured time bound."""

        try:
            async with asyncio.timeout(self._settings.timeout_seconds):
                response = await self._get(query.query)
        except TimeoutError as exc:
            raise ExternalKnowledgeError(
                f"NVD call exceeded the {self._settings.timeout_seconds}s "
                f"execution bound."
            ) from exc
        except httpx.HTTPError as exc:
            # Transport-level failure (connect/read/write, DNS, TLS...).
            raise ExternalKnowledgeError(
                f"NVD transport failure: {type(exc).__name__}."
            ) from exc

        if response.status_code != 200:
            raise ExternalKnowledgeError(
                f"NVD returned HTTP {response.status_code}: "
                f"{response.text[:_ERROR_DETAIL_LIMIT]}"
            )
        items = self._extract_items(response)
        logger.info(
            "nvd lookup ok items=%s",
            len(items),
        )
        return items

    async def _get(self, query: str) -> httpx.Response:
        cve_id = _CVE_ID.search(query)
        params: dict[str, str] = (
            {"cveId": cve_id.group(0).upper()}
            if cve_id
            else {
                "keywordSearch": query[:_QUERY_LIMIT],
                "resultsPerPage": str(self._settings.results_limit),
            }
        )
        headers = {"Accept": "application/json"}
        if self._api_key is not None:
            # The key travels only as a header, never in the URL, so it can
            # never leak through exception messages carrying the URL.
            headers["apiKey"] = self._api_key.reveal().strip()

        timeout = httpx.Timeout(self._settings.timeout_seconds)
        async with httpx.AsyncClient(
            timeout=timeout, transport=self._transport
        ) as client:
            return await client.get(
                _BASE_URL, params=params, headers=headers
            )

    def _extract_items(
        self, response: httpx.Response
    ) -> tuple[ExternalKnowledgeItem, ...]:
        try:
            payload = response.json()
        except ValueError as exc:
            raise ExternalKnowledgeError(
                "NVD returned a malformed (non-JSON) response body."
            ) from exc
        if not isinstance(payload, dict):
            raise ExternalKnowledgeError(
                "NVD returned an unexpected response shape."
            )
        vulnerabilities = payload.get("vulnerabilities")
        if not isinstance(vulnerabilities, list):
            raise ExternalKnowledgeError(
                "NVD returned no vulnerabilities list."
            )

        items: list[ExternalKnowledgeItem] = []
        for entry in vulnerabilities[: self._settings.results_limit]:
            item = self._to_item(entry)
            if item is None:
                # A malformed item inside a valid payload is skipped
                # (external data quality is not this platform's contract).
                logger.debug("nvd item skipped (invalid shape)")
                continue
            items.append(item)
        return tuple(items)

    @staticmethod
    def _to_item(entry: object) -> ExternalKnowledgeItem | None:
        if not isinstance(entry, dict):
            return None
        cve = entry.get("cve")
        if not isinstance(cve, dict):
            return None
        cve_id = cve.get("id")
        if not isinstance(cve_id, str) or not cve_id.strip():
            return None

        description = ""
        descriptions = cve.get("descriptions")
        if isinstance(descriptions, list):
            texts = [
                candidate.get("value")
                for candidate in descriptions
                if isinstance(candidate, dict)
            ]
            english = [
                candidate.get("value")
                for candidate in descriptions
                if isinstance(candidate, dict)
                and candidate.get("lang") == "en"
            ]
            chosen = next(
                (text for text in english + texts if isinstance(text, str)),
                None,
            )
            if chosen is not None:
                description = chosen.strip()
        if not description:
            description = "No description provided."

        return ExternalKnowledgeItem(
            source=_SOURCE,
            reference=cve_id.strip(),
            content=f"{cve_id.strip()}: {description[:_CONTENT_LIMIT]}",
            confidence=_NEUTRAL_CONFIDENCE,
        )
