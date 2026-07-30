"""Safe installation and validation of versioned Benchwork plugin archives."""

from __future__ import annotations

import json
import os
import shutil
import stat
import tarfile
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any

from ..schema_validation import validate_instance
from .state import InstallDocumentError, installer_data_root, sha256_file, strict_json_file


MAX_ARCHIVE_SIZE = 25 * 1024 * 1024
MAX_EXTRACTED_SIZE = 50 * 1024 * 1024
MAX_MEMBER_SIZE = 5 * 1024 * 1024
MAX_MEMBERS = 1000


def _safe_member_name(raw: str) -> PurePosixPath:
    if not raw or raw.startswith("/") or "\\" in raw:
        raise InstallDocumentError(f"unsafe archive path: {raw!r}")
    if any(ord(character) < 32 or ord(character) == 127 for character in raw):
        raise InstallDocumentError("archive path contains a control character")
    path = PurePosixPath(raw)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise InstallDocumentError(f"unsafe archive path: {raw!r}")
    return path


def _members(archive: tarfile.TarFile) -> list[tuple[tarfile.TarInfo, PurePosixPath]]:
    members = archive.getmembers()
    if len(members) > MAX_MEMBERS:
        raise InstallDocumentError("plugin archive contains too many entries")
    total = 0
    seen: set[str] = set()
    result: list[tuple[tarfile.TarInfo, PurePosixPath]] = []
    for member in members:
        path = _safe_member_name(member.name)
        folded = path.as_posix().casefold()
        if folded in seen:
            raise InstallDocumentError(f"duplicate plugin archive path: {member.name}")
        seen.add(folded)
        if not (member.isdir() or member.isfile()):
            raise InstallDocumentError(f"plugin archive entry is not a regular file: {member.name}")
        if member.size < 0 or member.size > MAX_MEMBER_SIZE:
            raise InstallDocumentError(f"plugin archive member is oversized: {member.name}")
        total += member.size
        if total > MAX_EXTRACTED_SIZE:
            raise InstallDocumentError("plugin archive expands beyond the size limit")
        result.append((member, path))
    return result


def extract_plugin_archive(archive_path: Path, destination: Path) -> None:
    if archive_path.stat().st_size > MAX_ARCHIVE_SIZE:
        raise InstallDocumentError("plugin archive exceeds the download size limit")
    destination.mkdir(parents=True, mode=0o700)
    with tarfile.open(archive_path, mode="r:gz") as archive:
        for member, relative in _members(archive):
            target = destination.joinpath(*relative.parts)
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True, mode=0o700)
                continue
            target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            source = archive.extractfile(member)
            if source is None:
                raise InstallDocumentError(f"cannot read plugin archive member: {member.name}")
            with source, target.open("xb") as output:
                shutil.copyfileobj(source, output, length=1024 * 1024)
            mode = 0o700 if member.mode & stat.S_IXUSR else 0o600
            target.chmod(mode)


def marketplace_root(extracted: Path) -> Path:
    if (extracted / ".agents" / "plugins" / "marketplace.json").is_file():
        return extracted
    children = [path for path in extracted.iterdir() if path.is_dir()]
    if len(children) == 1 and (
        children[0] / ".agents" / "plugins" / "marketplace.json"
    ).is_file():
        return children[0]
    raise InstallDocumentError("plugin archive does not contain a marketplace root")


def validate_plugin(root: Path, expected_version: str) -> dict[str, Any]:
    marketplace = strict_json_file(
        root / ".agents" / "plugins" / "marketplace.json",
        "Codex marketplace",
    )
    plugins = marketplace.get("plugins")
    if marketplace.get("name") != "benchwork-local" or not isinstance(plugins, list):
        raise InstallDocumentError("invalid Benchwork marketplace metadata")
    plugin_root = root / "plugins" / "benchwork"
    manifest = strict_json_file(
        plugin_root / ".codex-plugin" / "plugin.json",
        "Codex plugin manifest",
    )
    if manifest.get("name") != "benchwork" or manifest.get("version") != expected_version:
        raise InstallDocumentError("Codex plugin manifest version does not match release")
    compatibility = strict_json_file(
        plugin_root / "benchwork-plugin-api.json",
        "plugin compatibility metadata",
    )
    validate_instance("benchwork-plugin-api-1.0.json", compatibility)
    if compatibility["plugin_version"] != expected_version:
        raise InstallDocumentError("plugin compatibility version does not match release")
    skills = sorted((plugin_root / "skills").glob("*/skill.yaml"))
    if not skills:
        raise InstallDocumentError("plugin archive contains no Skill metadata")
    for skill in skills:
        metadata = strict_json_file(skill, f"Skill metadata {skill.parent.name}")
        validate_instance("benchwork-skill-metadata-1.0.json", metadata)
        if not (skill.parent / "SKILL.md").is_file():
            raise InstallDocumentError(f"Skill instructions are missing: {skill.parent.name}")
    return {
        "marketplace": marketplace["name"],
        "plugin": manifest["name"],
        "plugin_version": manifest["version"],
        "skill_count": len(skills),
        "path": str(root),
    }


def install_plugin_archive(
    archive_path: Path,
    *,
    expected_sha256: str,
    version: str,
    scope: str,
    data_root: Path,
    project_root: Path | None = None,
) -> dict[str, Any]:
    actual = sha256_file(archive_path)
    if actual != expected_sha256:
        raise InstallDocumentError(
            f"plugin checksum mismatch: expected {expected_sha256}, computed {actual}"
        )
    if scope == "project":
        if project_root is None or not project_root.is_absolute():
            raise InstallDocumentError("project plugin scope requires an absolute project root")
        if not project_root.is_dir():
            raise InstallDocumentError("project plugin root must be an existing directory")
        existing_marketplace = project_root / ".agents" / "plugins" / "marketplace.json"
        if existing_marketplace.exists():
            existing_document = strict_json_file(
                existing_marketplace,
                "project Codex marketplace",
            )
            if existing_document.get("name") != "benchwork-local":
                raise InstallDocumentError(
                    "project already has a differently named Codex marketplace"
                )
        plugin_base = project_root / ".agents" / "benchwork-installer" / "plugins"
    elif scope == "user":
        plugin_base = data_root / "plugins"
    else:
        return {
            "scope": "none",
            "version": None,
            "path": None,
            "marketplace_path": None,
            "previous_path": None,
        }

    plugin_base.mkdir(parents=True, exist_ok=True, mode=0o700)
    staging_path = Path(tempfile.mkdtemp(prefix=".plugin-stage-", dir=plugin_base))
    previous_path: str | None = None
    original_current_path: Path | None = None
    target: Path | None = None
    target_created = False
    current_changed = False
    marketplace_path: Path | None = None
    marketplace_existed = False
    marketplace_original: bytes | None = None
    try:
        unpacked = staging_path / "unpacked"
        extract_plugin_archive(archive_path, unpacked)
        root = marketplace_root(unpacked)
        validate_plugin(root, version)
        target = plugin_base / version
        if target.exists():
            validate_plugin(target, version)
        else:
            os.replace(root, target)
            target_created = True
        current = plugin_base / "current"
        if current.is_symlink():
            try:
                previous = current.resolve(strict=True)
                original_current_path = previous
                if previous != target and previous.parent == plugin_base:
                    previous_path = str(previous)
            except FileNotFoundError:
                pass
        elif current.exists():
            raise InstallDocumentError("plugin current pointer is not an installer-owned symlink")
        pointer = plugin_base / f".current-{os.getpid()}"
        try:
            pointer.symlink_to(target.name, target_is_directory=True)
            os.replace(pointer, current)
            current_changed = True
        finally:
            pointer.unlink(missing_ok=True)
        result: dict[str, Any] = {
            "scope": scope,
            "version": version,
            "path": str(target),
            "marketplace_path": str(target),
            "previous_path": previous_path,
            "_rollback_current_path": (
                str(original_current_path)
                if original_current_path is not None
                else None
            ),
        }
        if scope == "project":
            assert project_root is not None
            marketplace_path = project_root / ".agents" / "plugins" / "marketplace.json"
            marketplace_existed = marketplace_path.exists()
            backup = None
            if marketplace_existed:
                marketplace_original = marketplace_path.read_bytes()
                document = strict_json_file(marketplace_path, "project Codex marketplace")
                if document.get("name") != "benchwork-local":
                    raise InstallDocumentError(
                        "project already has a differently named Codex marketplace"
                    )
                blob = marketplace_path.read_bytes()
                backup_root = installer_data_root() / "backups"
                backup_root.mkdir(parents=True, exist_ok=True, mode=0o700)
                backup_path = backup_root / (
                    f"marketplace.{sha256_file(marketplace_path)[:12]}.bak"
                )
                backup_path.write_bytes(blob)
                backup_path.chmod(0o600)
                backup = {
                    "source": str(marketplace_path),
                    "backup": str(backup_path),
                    "source_sha256": sha256_file(marketplace_path),
                }
                plugins = document.get("plugins")
                if not isinstance(plugins, list):
                    raise InstallDocumentError("project marketplace plugins must be an array")
                document["plugins"] = [
                    entry
                    for entry in plugins
                    if not isinstance(entry, dict) or entry.get("name") != "benchwork"
                ]
            else:
                document = {
                    "name": "benchwork-local",
                    "interface": {"displayName": "Benchwork Local"},
                    "plugins": [],
                }
            document["plugins"].append(
                {
                    "name": "benchwork",
                    "source": {
                        "source": "local",
                        "path": "./.agents/benchwork-installer/plugins/current/plugins/benchwork",
                    },
                    "policy": {
                        "installation": "AVAILABLE",
                        "authentication": "ON_INSTALL",
                    },
                    "category": "Productivity",
                }
            )
            marketplace_path.parent.mkdir(parents=True, exist_ok=True)
            temporary = marketplace_path.with_name(f".marketplace-{os.getpid()}.json")
            temporary.write_text(
                json.dumps(document, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            os.replace(temporary, marketplace_path)
            result["marketplace_path"] = str(project_root)
            result["_marketplace_file"] = str(marketplace_path)
            result["_marketplace_sha256"] = sha256_file(marketplace_path)
            result["_marketplace_backup"] = backup
        retained = {target.resolve()}
        if previous_path is not None:
            retained.add(Path(previous_path).resolve())
        for candidate in plugin_base.iterdir():
            if (
                candidate.is_dir()
                and not candidate.name.startswith(".")
                and candidate.resolve() not in retained
            ):
                shutil.rmtree(candidate)
        return result
    except BaseException:
        if marketplace_path is not None:
            if marketplace_existed and marketplace_original is not None:
                temporary = marketplace_path.with_name(
                    f".marketplace-rollback-{os.getpid()}.json"
                )
                temporary.write_bytes(marketplace_original)
                os.replace(temporary, marketplace_path)
            elif not marketplace_existed:
                marketplace_path.unlink(missing_ok=True)
        if current_changed:
            current = plugin_base / "current"
            if original_current_path is None:
                current.unlink(missing_ok=True)
            else:
                pointer = plugin_base / f".rollback-current-{os.getpid()}"
                try:
                    pointer.symlink_to(
                        original_current_path.name,
                        target_is_directory=True,
                    )
                    os.replace(pointer, current)
                finally:
                    pointer.unlink(missing_ok=True)
        if target_created and target is not None:
            shutil.rmtree(target, ignore_errors=True)
        raise
    finally:
        shutil.rmtree(staging_path, ignore_errors=True)
