"""Tests for the content-addressed filesystem payload store (ES-060).

The adapter resolves only well-formed ``sha256:<64 hex>`` addresses to paths —
the address validation doubles as the path-traversal guard — writes atomically
and idempotently, and reports unresolvable addresses as ``None``/``False``
rather than errors. Temp-directory backed; plain functions, ``asyncio.run``.
"""

import asyncio
import tempfile
from pathlib import Path

from app.application.investigation import payload_address
from app.infrastructure.objectstore import FilesystemEvidencePayloadStore

_CONTENT = b"raw evidence payload"


def test_put_get_roundtrip() -> None:
    async def scenario(root: Path) -> None:
        store = FilesystemEvidencePayloadStore(root)
        address = payload_address(_CONTENT)

        await store.put(address, _CONTENT)

        assert await store.get(address) == _CONTENT
        assert await store.exists(address)

    with tempfile.TemporaryDirectory() as directory:
        asyncio.run(scenario(Path(directory)))


def test_put_is_idempotent() -> None:
    async def scenario(root: Path) -> None:
        store = FilesystemEvidencePayloadStore(root)
        address = payload_address(_CONTENT)

        await store.put(address, _CONTENT)
        await store.put(address, _CONTENT)

        assert await store.get(address) == _CONTENT

    with tempfile.TemporaryDirectory() as directory:
        asyncio.run(scenario(Path(directory)))


def test_layout_is_content_addressed_under_the_root() -> None:
    async def scenario(root: Path) -> None:
        store = FilesystemEvidencePayloadStore(root)
        address = payload_address(_CONTENT)
        digest = address.removeprefix("sha256:")

        await store.put(address, _CONTENT)

        assert (root / "sha256" / digest[:2] / digest).is_file()

    with tempfile.TemporaryDirectory() as directory:
        asyncio.run(scenario(Path(directory)))


def test_unknown_address_resolves_to_none() -> None:
    async def scenario(root: Path) -> None:
        store = FilesystemEvidencePayloadStore(root)

        assert await store.get(payload_address(b"never stored")) is None
        assert not await store.exists(payload_address(b"never stored"))

    with tempfile.TemporaryDirectory() as directory:
        asyncio.run(scenario(Path(directory)))


def test_hostile_addresses_never_touch_the_filesystem() -> None:
    async def scenario(root: Path) -> None:
        store = FilesystemEvidencePayloadStore(root)
        outside = root.parent / "outside.txt"
        outside.write_bytes(b"secret")

        for hostile in (
            "sha256:../../outside.txt",
            "../outside.txt",
            "sha256:" + "A" * 64,  # uppercase: not a well-formed address
            "",
        ):
            assert await store.get(hostile) is None
            assert not await store.exists(hostile)

    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory) / "store"
        root.mkdir()
        asyncio.run(scenario(root))


def test_put_rejects_malformed_address_as_programming_error() -> None:
    async def scenario(root: Path) -> None:
        store = FilesystemEvidencePayloadStore(root)

        try:
            await store.put("not-an-address", _CONTENT)
        except ValueError:
            return
        raise AssertionError("Expected ValueError for a malformed address.")

    with tempfile.TemporaryDirectory() as directory:
        asyncio.run(scenario(Path(directory)))
