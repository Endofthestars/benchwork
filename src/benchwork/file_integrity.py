"""Bounded-memory integrity helpers for file-backed project artifacts."""

from __future__ import annotations

import hashlib
from pathlib import Path


FILE_HASH_CHUNK_BYTES = 1024 * 1024


def file_sigil(path: Path) -> str:
    """Return the canonical SHA-256 Sigil without loading the whole file."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(FILE_HASH_CHUNK_BYTES), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()
