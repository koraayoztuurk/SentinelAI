"""Content-addressed filesystem evidence payload store (ES-060, ADR-015 §4).

Dev-grade first realization of the application-layer
:class:`~app.application.investigation.payload_store.EvidencePayloadStore`
port: payloads live under a configured root in a content-addressed layout
(``<root>/sha256/<first two hex>/<hex>``). The adapter never mints addresses —
the application computes them (ADR-015 §2); it only resolves well-formed
addresses to paths, which doubles as the **path-traversal guard**: anything
that is not exactly ``sha256:<64 lowercase hex>`` resolves nowhere (``get``
→ ``None``, ``exists`` → ``False``) and never touches the filesystem.

Writes are idempotent (content addressing: an existing payload is left as it
is) and atomic (temp file + ``os.replace``) so a crashed upload never leaves a
partially written payload at its final address. Operational failures map to
``EvidencePayloadStoreUnavailableError``; a malformed address passed to
``put`` is a programming-contract violation (the application always derives
it) and raises ``ValueError``.

The file I/O is synchronous inside the async port — acceptable for the
dev-grade adapter (small bounded payloads, local disk); the production
S3-compatible adapter (Milestone G) owns real async transport.
"""

import logging
import os
import tempfile
from pathlib import Path

from app.application.investigation.errors import (
    EvidencePayloadStoreUnavailableError,
)
from app.application.investigation.payload_store import (
    PAYLOAD_ADDRESS_PREFIX,
    is_payload_address,
)

logger = logging.getLogger(__name__)


class FilesystemEvidencePayloadStore:
    """``EvidencePayloadStore`` over a content-addressed directory layout."""

    def __init__(self, root: Path) -> None:
        self._root = root

    def _path_of(self, address: str) -> Path | None:
        """Resolve a well-formed address to its path; ``None`` otherwise."""

        if not is_payload_address(address):
            return None
        digest = address.removeprefix(PAYLOAD_ADDRESS_PREFIX)
        return self._root / "sha256" / digest[:2] / digest

    async def put(self, address: str, content: bytes) -> None:
        """Store the payload at its address (idempotent, atomic)."""

        path = self._path_of(address)
        if path is None:
            raise ValueError(f"Malformed payload address '{address}'.")
        try:
            if path.is_file():
                # Content-addressed: the existing payload is the payload.
                return
            path.parent.mkdir(parents=True, exist_ok=True)
            descriptor, temp_name = tempfile.mkstemp(
                dir=path.parent, prefix=".upload-"
            )
            try:
                with os.fdopen(descriptor, "wb") as handle:
                    handle.write(content)
                os.replace(temp_name, path)
            except OSError:
                # Best-effort cleanup; the original failure is what matters.
                try:
                    os.unlink(temp_name)
                except OSError:
                    pass
                raise
        except OSError as exc:
            raise EvidencePayloadStoreUnavailableError(
                f"The payload store cannot write ({type(exc).__name__})."
            ) from exc
        logger.info(
            "payload stored address=%s size=%s", address, len(content)
        )

    async def get(self, address: str) -> bytes | None:
        """Return the payload bytes, or ``None`` when unresolvable."""

        path = self._path_of(address)
        if path is None:
            return None
        try:
            return path.read_bytes()
        except FileNotFoundError:
            return None
        except OSError as exc:
            raise EvidencePayloadStoreUnavailableError(
                f"The payload store cannot read ({type(exc).__name__})."
            ) from exc

    async def exists(self, address: str) -> bool:
        """Return whether the address resolves to a stored payload."""

        path = self._path_of(address)
        return path is not None and path.is_file()

    async def erase(self, address: str) -> None:
        """Physically delete the payload (ADR-017 §6, dev-grade strategy).

        Physical deletion is practical on a mutable single-node filesystem, so
        it is this adapter's erasure strategy; crypto-shredding is the
        designated strategy for the immutable production object store
        (Milestone G). Idempotent: an unresolvable or already-erased address is
        a no-op, so the erasure projection is safely retriable.
        """

        path = self._path_of(address)
        if path is None:
            return
        try:
            path.unlink()
        except FileNotFoundError:
            return
        except OSError as exc:
            raise EvidencePayloadStoreUnavailableError(
                f"The payload store cannot erase ({type(exc).__name__})."
            ) from exc
        logger.info("payload erased address=%s", address)
