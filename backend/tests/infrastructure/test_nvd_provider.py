"""Contract tests for the NVD CVE external knowledge provider (ES-058).

Deterministic, network-free validation over ``httpx.MockTransport``: the
adapter realizes the ``ExternalKnowledgeProvider`` port contract — bounded
execution time, total error mapping to ``ExternalKnowledgeError`` (transport,
non-success statuses, malformed payloads), optional-key hygiene (``apiKey``
header only, keyless degrade, never part of an error message), explicit
CVE-id resolution and bounded keyword search. Plain test functions.
"""

import asyncio

import httpx
import pytest

from app.ai.errors import ExternalKnowledgeError
from app.ai.providers.external import (
    ExternalKnowledgeItem,
    ExternalKnowledgeQuery,
)
from app.application.secrets import SecretName, SecretNotFoundError
from app.config.ai import NvdSettings
from app.infrastructure.ai.nvd import NvdCveProvider
from app.shared.secret import Secret

_API_KEY = "nvd-test-key-4471"


class _FixedSecrets:
    """SecretProvider double returning one fixed key."""

    def resolve(self, name: SecretName) -> Secret:
        assert name == SecretName("NVD_API_KEY")
        return Secret(_API_KEY)


class _EmptySecrets:
    """SecretProvider double without any configured secret."""

    def resolve(self, name: SecretName) -> Secret:
        raise SecretNotFoundError(f"Secret '{name}' is not configured.")


def _settings(timeout_seconds: float = 5.0) -> NvdSettings:
    return NvdSettings(timeout_seconds=timeout_seconds, results_limit=3)


def _provider(
    transport: httpx.MockTransport,
    timeout_seconds: float = 5.0,
    keyless: bool = False,
) -> NvdCveProvider:
    return NvdCveProvider(
        _settings(timeout_seconds),
        _EmptySecrets() if keyless else _FixedSecrets(),
        transport=transport,
    )


def _lookup(provider: NvdCveProvider, query: str) -> tuple[ExternalKnowledgeItem, ...]:
    return asyncio.run(provider.lookup(ExternalKnowledgeQuery(query=query)))


def _vulnerability(cve_id: str, description: str) -> dict[str, object]:
    return {
        "cve": {
            "id": cve_id,
            "descriptions": [
                {"lang": "es", "value": "otra descripción"},
                {"lang": "en", "value": description},
            ],
        }
    }


def _success_body(*entries: dict[str, object]) -> dict[str, object]:
    return {"totalResults": len(entries), "vulnerabilities": list(entries)}


# ----------------------------------------------------------------- happy path


def test_lookup_maps_vulnerabilities_and_sends_key_only_as_header() -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(
            200,
            json=_success_body(
                _vulnerability("CVE-2024-0001", "A remote code execution flaw."),
                _vulnerability("CVE-2024-0002", "A privilege escalation flaw."),
            ),
        )

    provider = _provider(httpx.MockTransport(handler))
    items = _lookup(provider, "remote code execution in ExampleServer")

    assert [item.reference for item in items] == [
        "CVE-2024-0001",
        "CVE-2024-0002",
    ]
    first = items[0]
    assert first.source == "nvd"
    # The English description is chosen; the id anchors the content.
    assert first.content == "CVE-2024-0001: A remote code execution flaw."
    assert first.confidence.value == 0.5

    request = captured[0]
    assert request.headers["apiKey"] == _API_KEY
    # Key hygiene: never in the URL.
    assert _API_KEY not in str(request.url)
    assert request.url.params["keywordSearch"] == (
        "remote code execution in ExampleServer"
    )
    assert request.url.params["resultsPerPage"] == "3"


def test_lookup_without_configured_key_degrades_to_keyless() -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, json=_success_body())

    provider = _provider(httpx.MockTransport(handler), keyless=True)
    assert _lookup(provider, "anything") == ()
    assert "apiKey" not in captured[0].headers


def test_explicit_cve_id_resolves_directly() -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(
            200,
            json=_success_body(
                _vulnerability("CVE-2021-44228", "JNDI lookup remote code execution.")
            ),
        )

    provider = _provider(httpx.MockTransport(handler))
    items = _lookup(provider, "check cve-2021-44228 exposure on HOST-1")

    assert [item.reference for item in items] == ["CVE-2021-44228"]
    request = captured[0]
    assert request.url.params["cveId"] == "CVE-2021-44228"
    assert "keywordSearch" not in request.url.params


def test_keyword_query_is_bounded() -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, json=_success_body())

    provider = _provider(httpx.MockTransport(handler))
    _lookup(provider, "x" * 1000)

    assert len(captured[0].url.params["keywordSearch"]) == 256


def test_results_are_bounded_even_when_the_payload_overflows() -> None:
    entries = [
        _vulnerability(f"CVE-2024-000{index}", "flaw") for index in range(6)
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_success_body(*entries))

    provider = _provider(httpx.MockTransport(handler))
    assert len(_lookup(provider, "flaw")) == 3


def test_malformed_item_is_skipped_not_fatal() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "vulnerabilities": [
                    "not-an-object",
                    {"cve": {"id": ""}},
                    _vulnerability("CVE-2024-0009", "A valid entry."),
                ]
            },
        )

    provider = _provider(httpx.MockTransport(handler))
    items = _lookup(provider, "valid")

    assert [item.reference for item in items] == ["CVE-2024-0009"]


# -------------------------------------------------------------- error mapping


def test_http_error_maps_to_external_knowledge_error_without_key() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, text="rate limited")

    provider = _provider(httpx.MockTransport(handler))
    with pytest.raises(ExternalKnowledgeError) as excinfo:
        _lookup(provider, "anything")

    assert "HTTP 403" in str(excinfo.value)
    assert _API_KEY not in str(excinfo.value)


def test_malformed_json_maps_to_external_knowledge_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="<html>maintenance</html>")

    provider = _provider(httpx.MockTransport(handler))
    with pytest.raises(ExternalKnowledgeError):
        _lookup(provider, "anything")


def test_missing_vulnerabilities_list_maps_to_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"message": "unexpected"})

    provider = _provider(httpx.MockTransport(handler))
    with pytest.raises(ExternalKnowledgeError):
        _lookup(provider, "anything")


def test_transport_failure_maps_to_external_knowledge_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom")

    provider = _provider(httpx.MockTransport(handler))
    with pytest.raises(ExternalKnowledgeError) as excinfo:
        _lookup(provider, "anything")

    assert "transport" in str(excinfo.value)


def test_execution_bound_is_enforced() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        await asyncio.sleep(0.5)
        return httpx.Response(200, json=_success_body())

    provider = _provider(httpx.MockTransport(handler), timeout_seconds=0.05)
    with pytest.raises(ExternalKnowledgeError) as excinfo:
        _lookup(provider, "anything")

    assert "execution bound" in str(excinfo.value)
