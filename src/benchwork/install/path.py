"""Idempotent, opt-in PATH block management."""

from __future__ import annotations

import hashlib
import os
import re
import stat
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .state import InstallDocumentError, installer_data_root, reject_control_characters


START = "# >>> benchwork installer >>>"
END = "# <<< benchwork installer <<<"
BLOCK = re.compile(rf"(?ms)^{re.escape(START)}\r?\n.*?^{re.escape(END)}\r?\n?")


def _profile() -> tuple[Path, str]:
    shell = Path(os.environ.get("SHELL", "")).name
    if shell == "zsh":
        return Path.home() / ".zshrc", "posix"
    if shell == "bash":
        return (
            Path.home() / (".bash_profile" if sys.platform == "darwin" else ".bashrc"),
            "posix",
        )
    if shell == "fish":
        return Path.home() / ".config" / "fish" / "config.fish", "fish"
    if shell in {"sh", "dash", "ksh"}:
        return Path.home() / ".profile", "posix"
    raise InstallDocumentError(
        "cannot select a shell profile; add the reported export command manually"
    )


def _quote(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"


def _render(bin_dir: Path, syntax: str, newline: str) -> str:
    quoted = _quote(str(bin_dir))
    if syntax == "fish":
        lines = [
            START,
            f"if not contains -- {quoted} $PATH",
            f"    set -gx PATH {quoted} $PATH",
            "end",
            END,
            "",
        ]
    else:
        lines = [
            START,
            f"benchwork_bin={quoted}",
            'case ":$PATH:" in *":$benchwork_bin:"*) ;; *) export PATH="$benchwork_bin:$PATH" ;; esac',
            "unset benchwork_bin",
            END,
            "",
        ]
    return newline.join(lines)


def ensure_path_block(bin_dir: Path, *, dry_run: bool = False) -> tuple[dict[str, Any], dict[str, str] | None]:
    if not bin_dir.is_absolute():
        raise InstallDocumentError("binary directory must be absolute")
    reject_control_characters(str(bin_dir), "binary directory")
    profile, syntax = _profile()
    original = profile.read_bytes() if profile.exists() else b""
    try:
        text = original.decode("utf-8")
    except UnicodeDecodeError as error:
        raise InstallDocumentError(f"shell profile is not UTF-8: {profile}") from error
    newline = "\r\n" if b"\r\n" in original else "\n"
    rendered = _render(bin_dir, syntax, newline)
    updated = BLOCK.sub("", text)
    if updated and not updated.endswith(("\n", "\r")):
        updated += newline
    updated += rendered
    digest = hashlib.sha256(updated.encode("utf-8")).hexdigest()
    backup: dict[str, str] | None = None
    if not dry_run and updated.encode("utf-8") != original:
        profile.parent.mkdir(parents=True, exist_ok=True)
        if profile.exists():
            backup_root = installer_data_root() / "backups"
            backup_root.mkdir(parents=True, exist_ok=True, mode=0o700)
            stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
            target = backup_root / f"{profile.name}.{stamp}.path.bak"
            target.write_bytes(original)
            target.chmod(0o600)
            backup = {
                "source": str(profile),
                "backup": str(target),
                "source_sha256": hashlib.sha256(original).hexdigest(),
            }
            mode = stat.S_IMODE(profile.stat().st_mode)
        else:
            mode = 0o600
        profile.write_text(updated, encoding="utf-8", newline="")
        profile.chmod(mode)
    return {"path": str(profile), "kind": "path_block", "sha256": digest}, backup


def remove_path_block(path: Path, *, dry_run: bool = False) -> None:
    if not path.is_file():
        return
    original_blob = path.read_bytes()
    try:
        original = original_blob.decode("utf-8")
    except UnicodeDecodeError as error:
        raise InstallDocumentError(f"shell profile is not UTF-8: {path}") from error
    updated = BLOCK.sub("", original)
    if updated != original and not dry_run:
        path.write_bytes(updated.encode("utf-8"))
