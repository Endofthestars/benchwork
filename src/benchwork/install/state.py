"""Strict installer documents and atomic installer-owned state."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from ..schema_validation import validate_instance


STATE_SCHEMA = "benchwork-install-state-1.0.json"
MANIFEST_SCHEMA = "benchwork-release-manifest-1.0.json"


class InstallDocumentError(ValueError):
    """An installer document failed strict parsing or validation."""


def reject_control_characters(value: str, label: str) -> None:
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise InstallDocumentError(f"{label} contains a control character")


def strict_json_bytes(blob: bytes, label: str = "JSON") -> dict[str, Any]:
    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise InstallDocumentError(f"{label} contains duplicate key: {key}")
            result[key] = value
        return result

    try:
        document = json.loads(
            blob.decode("utf-8"),
            object_pairs_hook=reject_duplicates,
        )
    except UnicodeDecodeError as error:
        raise InstallDocumentError(f"{label} is not UTF-8") from error
    except json.JSONDecodeError as error:
        raise InstallDocumentError(f"{label} is invalid JSON: {error.msg}") from error
    if not isinstance(document, dict):
        raise InstallDocumentError(f"{label} must contain a JSON object")
    return document


def strict_json_file(path: Path, label: str | None = None) -> dict[str, Any]:
    try:
        blob = path.read_bytes()
    except OSError as error:
        raise InstallDocumentError(f"cannot read {label or path}: {error}") from error
    return strict_json_bytes(blob, label or str(path))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def installer_data_root() -> Path:
    configured = os.environ.get("XDG_DATA_HOME")
    base = Path(configured).expanduser() if configured else Path.home() / ".local" / "share"
    return base / "benchwork"


def installer_cache_root() -> Path:
    configured = os.environ.get("XDG_CACHE_HOME")
    base = Path(configured).expanduser() if configured else Path.home() / ".cache"
    return base / "benchwork"


def state_path() -> Path:
    override = os.environ.get("BENCHWORK_INSTALL_STATE")
    return Path(override).expanduser() if override else installer_data_root() / "install-state.json"


def load_state(*, required: bool = False) -> dict[str, Any] | None:
    path = state_path()
    if not path.exists():
        if required:
            raise InstallDocumentError(f"installer state does not exist: {path}")
        return None
    state = strict_json_file(path, "installer state")
    validate_instance(STATE_SCHEMA, state)
    return state


def write_state(state: dict[str, Any]) -> Path:
    validate_instance(STATE_SCHEMA, state)
    path = state_path()
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    payload = (json.dumps(state, indent=2, sort_keys=True) + "\n").encode("utf-8")
    descriptor, temporary = tempfile.mkstemp(
        prefix=".install-state-",
        suffix=".json",
        dir=path.parent,
    )
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise
    return path


def load_manifest(path: Path) -> dict[str, Any]:
    manifest = strict_json_file(path, "release manifest")
    validate_instance(MANIFEST_SCHEMA, manifest)
    version = manifest["version"]
    if manifest["tag"] != f"v{version}":
        raise InstallDocumentError("manifest tag does not match package version")
    if manifest["package"]["requirement"] != f"benchwork-arcana=={version}":
        raise InstallDocumentError("manifest package requirement is not exact")
    if manifest["plugin"]["runtime_requirement"] != f"benchwork-arcana=={version}":
        raise InstallDocumentError("manifest plugin runtime requirement does not match")
    expected_plugin = pep440_to_plugin_version(version)
    if manifest["plugin"]["version"] != expected_plugin:
        raise InstallDocumentError("manifest plugin version does not match package version")
    prerelease = "rc" if "rc" in version else "nightly" if "dev" in version else "stable"
    if manifest["channel"] != prerelease:
        raise InstallDocumentError("manifest channel does not match package version")
    return manifest


def pep440_to_plugin_version(version: str) -> str:
    for marker, rendered in (("rc", "-rc."), ("a", "-alpha."), ("b", "-beta.")):
        if marker in version:
            prefix, suffix = version.rsplit(marker, 1)
            if suffix.isdigit():
                return f"{prefix}{rendered}{suffix}"
    return version
