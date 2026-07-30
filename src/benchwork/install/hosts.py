"""Host configuration through supported Host CLI commands."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Sequence

from .state import installer_data_root


class HostConfigurationError(ValueError):
    """A requested Host operation could not be completed safely."""


def _run(command: Sequence[str], *, timeout: int = 20) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            list(command),
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
            env={**os.environ, "NO_COLOR": "1"},
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise HostConfigurationError(f"cannot run {' '.join(command)}: {error}") from error


def _has_command(command: str) -> bool:
    return shutil.which(command) is not None


def _supports(command: Sequence[str], needle: str) -> bool:
    result = _run([*command, "--help"])
    return result.returncode == 0 and needle in (result.stdout + result.stderr)


def _backup(path: Path) -> dict[str, str] | None:
    if not path.is_file():
        return None
    blob = path.read_bytes()
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    backup_root = installer_data_root() / "backups"
    backup_root.mkdir(parents=True, exist_ok=True, mode=0o700)
    backup = backup_root / f"{path.name}.{stamp}.{hashlib.sha256(blob).hexdigest()[:12]}.bak"
    backup.write_bytes(blob)
    backup.chmod(0o600)
    return {
        "source": str(path),
        "backup": str(backup),
        "source_sha256": hashlib.sha256(blob).hexdigest(),
    }


def codex_check() -> dict[str, Any]:
    if not _has_command("codex"):
        return {
            "host": "codex",
            "detected": False,
            "mcp": "NOT_CONFIGURED",
            "plugin": "NOT_CONFIGURED",
            "action": "Install Codex separately, then rerun with --with-codex.",
        }
    version = _run(["codex", "--version"])
    mcp = _run(["codex", "mcp", "get", "benchwork"])
    plugins = _run(["codex", "plugin", "list"])
    combined = (plugins.stdout + plugins.stderr).lower()
    plugin_status = "PASS" if "benchwork" in combined else "NOT_CONFIGURED"
    mcp_status = "PASS" if mcp.returncode == 0 or plugin_status == "PASS" else "NOT_CONFIGURED"
    return {
        "host": "codex",
        "detected": True,
        "version": (version.stdout or version.stderr).strip(),
        "mcp": mcp_status,
        "plugin": plugin_status,
        "known_limitations": (
            ["Local marketplace refresh may require a fresh Codex process."]
            if plugin_status == "PASS"
            else []
        ),
        "action": (
            "Restart Codex and run bwork host check codex."
            if plugin_status == "PASS"
            else "Rerun the installer with --with-codex."
        ),
    }


def configure_codex(
    plugin_marketplace: Path | None,
    *,
    expected_version: str | None = None,
    previous_marketplace: Path | None = None,
    force: bool = False,
    dry_run: bool = False,
) -> tuple[dict[str, str], list[dict[str, str]]]:
    if not _has_command("codex"):
        raise HostConfigurationError("Codex CLI is not installed")
    backups: list[dict[str, str]] = []
    if plugin_marketplace is not None and _supports(["codex", "plugin"], "add"):
        marketplaces = _run(["codex", "plugin", "marketplace", "list", "--json"])
        plugins = _run(["codex", "plugin", "list", "--json"])
        try:
            marketplace_document = json.loads(marketplaces.stdout) if marketplaces.returncode == 0 else {}
            plugin_document = json.loads(plugins.stdout) if plugins.returncode == 0 else {}
        except json.JSONDecodeError as error:
            raise HostConfigurationError("Codex plugin inventory is not valid JSON") from error
        existing_marketplace = next(
            (
                entry
                for entry in marketplace_document.get("marketplaces", [])
                if isinstance(entry, dict) and entry.get("name") == "benchwork-local"
            ),
            None,
        )
        installed_plugin = next(
            (
                entry
                for entry in plugin_document.get("installed", [])
                if isinstance(entry, dict)
                and entry.get("pluginId") == "benchwork@benchwork-local"
            ),
            None,
        )
        existing_root = (
            Path(existing_marketplace["root"]).resolve()
            if isinstance(existing_marketplace, dict)
            and isinstance(existing_marketplace.get("root"), str)
            else None
        )
        requested_root = plugin_marketplace.resolve()
        replacing = existing_root is not None and existing_root != requested_root
        previous_matches = (
            previous_marketplace is not None
            and existing_root == previous_marketplace.resolve()
        )
        if replacing and not (previous_matches or force):
            raise HostConfigurationError(
                "Codex already has a non-installer-owned benchwork-local marketplace; "
                "remove it manually or rerun the installer with --force"
            )
        plugin_needs_install = (
            installed_plugin is None
            or installed_plugin.get("version") != expected_version
            or replacing
        )
        if not dry_run:
            if replacing or existing_root is None or plugin_needs_install:
                backup = _backup(Path.home() / ".codex" / "config.toml")
                if backup is not None:
                    backups.append(backup)
            marketplace_removed = False
            plugin_removed = False
            try:
                if replacing:
                    if installed_plugin is not None:
                        plugin_removal = _run(
                            ["codex", "plugin", "remove", "benchwork@benchwork-local"]
                        )
                        if plugin_removal.returncode != 0:
                            raise HostConfigurationError(
                                f"Codex plugin removal failed: "
                                f"{(plugin_removal.stderr or plugin_removal.stdout).strip()}"
                            )
                        plugin_removed = True
                    removal = _run(
                        ["codex", "plugin", "marketplace", "remove", "benchwork-local"]
                    )
                    if removal.returncode != 0:
                        raise HostConfigurationError(
                            f"Codex marketplace removal failed: "
                            f"{(removal.stderr or removal.stdout).strip()}"
                        )
                    marketplace_removed = True
                if existing_root is None or replacing:
                    addition = _run(
                        [
                            "codex",
                            "plugin",
                            "marketplace",
                            "add",
                            str(plugin_marketplace),
                        ]
                    )
                    if addition.returncode != 0:
                        raise HostConfigurationError(
                            f"Codex marketplace configuration failed: "
                            f"{(addition.stderr or addition.stdout).strip()}"
                        )
                if plugin_needs_install:
                    if installed_plugin is not None and not replacing:
                        plugin_removal = _run(
                            ["codex", "plugin", "remove", "benchwork@benchwork-local"]
                        )
                        if plugin_removal.returncode != 0:
                            raise HostConfigurationError(
                                f"Codex plugin removal failed: "
                                f"{(plugin_removal.stderr or plugin_removal.stdout).strip()}"
                            )
                        plugin_removed = True
                    addition = _run(
                        ["codex", "plugin", "add", "benchwork@benchwork-local"]
                    )
                    if addition.returncode != 0:
                        raise HostConfigurationError(
                            f"Codex plugin configuration failed: "
                            f"{(addition.stderr or addition.stdout).strip()}"
                        )
            except HostConfigurationError:
                if replacing and marketplace_removed and existing_root is not None:
                    _run(["codex", "plugin", "marketplace", "remove", "benchwork-local"])
                    _run(
                        [
                            "codex",
                            "plugin",
                            "marketplace",
                            "add",
                            str(existing_root),
                        ]
                    )
                if plugin_removed and installed_plugin is not None:
                    _run(["codex", "plugin", "add", "benchwork@benchwork-local"])
                raise
        return {"mcp": "plugin_managed", "plugin": "configured"}, backups

    commands = [["codex", "mcp", "add", "benchwork", "--", "bwork", "mcp", "serve"]]
    if not dry_run:
        existing = _run(["codex", "mcp", "get", "benchwork", "--json"])
        stale = False
        if existing.returncode == 0:
            try:
                document = json.loads(existing.stdout)
            except json.JSONDecodeError as error:
                raise HostConfigurationError(
                    "existing Codex MCP entry is not valid JSON"
                ) from error
            transport = document.get("transport", {})
            stale = (
                not isinstance(transport, dict)
                or transport.get("command") != "bwork"
                or transport.get("args") != ["mcp", "serve"]
            )
            if stale and not force:
                raise HostConfigurationError(
                    "Codex has a stale or non-installer-owned Benchwork MCP entry; "
                    "remove it manually or rerun with --force"
                )
            if stale:
                backup = _backup(Path.home() / ".codex" / "config.toml")
                if backup is not None:
                    backups.append(backup)
            if stale:
                removal = _run(["codex", "mcp", "remove", "benchwork"])
                if removal.returncode != 0:
                    raise HostConfigurationError(
                        f"Codex MCP removal failed: "
                        f"{(removal.stderr or removal.stdout).strip()}"
                    )
        if existing.returncode != 0 or stale:
            if not stale:
                backup = _backup(Path.home() / ".codex" / "config.toml")
                if backup is not None:
                    backups.append(backup)
            result = _run(commands[0])
            if result.returncode != 0:
                raise HostConfigurationError(
                    f"Codex MCP configuration failed: {(result.stderr or result.stdout).strip()}"
                )
    return {"mcp": "configured", "plugin": "unsupported"}, backups


def claude_check() -> dict[str, Any]:
    if not _has_command("claude"):
        return {
            "host": "claude",
            "detected": False,
            "mcp": "NOT_CONFIGURED",
            "plugin": "NOT_CONFIGURED",
            "action": "Install Claude Code separately, then rerun with --with-claude.",
        }
    version = _run(["claude", "--version"])
    mcp = _run(["claude", "mcp", "get", "benchwork"])
    return {
        "host": "claude",
        "detected": True,
        "version": (version.stdout or version.stderr).strip(),
        "mcp": "EXPERIMENTAL" if mcp.returncode == 0 else "NOT_CONFIGURED",
        "plugin": "NOT_CONFIGURED",
        "action": (
            "Run the documented Claude MCP acceptance trial."
            if mcp.returncode == 0
            else "Rerun the installer with --with-claude."
        ),
    }


def configure_claude(*, dry_run: bool = False) -> tuple[dict[str, str], list[dict[str, str]]]:
    if not _has_command("claude"):
        raise HostConfigurationError("Claude CLI is not installed")
    backups: list[dict[str, str]] = []
    if not dry_run:
        existing = _run(["claude", "mcp", "get", "benchwork"])
        if existing.returncode != 0:
            backup = _backup(Path.home() / ".claude.json")
            if backup is not None:
                backups.append(backup)
            result = _run(
                [
                    "claude",
                    "mcp",
                    "add",
                    "--scope",
                    "user",
                    "benchwork",
                    "--",
                    "bwork",
                    "mcp",
                    "serve",
                ]
            )
            if result.returncode != 0:
                raise HostConfigurationError(
                    f"Claude MCP configuration failed: {(result.stderr or result.stdout).strip()}"
                )
    return {"mcp": "experimental", "plugin": "not_configured"}, backups


def remove_installer_owned_hosts(state: dict[str, Any], *, dry_run: bool = False) -> None:
    def require_success(command: Sequence[str], label: str) -> None:
        result = _run(command)
        if result.returncode != 0:
            raise HostConfigurationError(
                f"{label} failed: {(result.stderr or result.stdout).strip()}"
            )

    codex = state["hosts"]["codex"]
    if _has_command("codex"):
        if codex["plugin"] == "configured" and not dry_run:
            inventory = _run(["codex", "plugin", "marketplace", "list", "--json"])
            if inventory.returncode != 0:
                raise HostConfigurationError("cannot inspect Codex marketplaces during uninstall")
            try:
                marketplaces = json.loads(inventory.stdout).get("marketplaces", [])
            except json.JSONDecodeError as error:
                raise HostConfigurationError(
                    "Codex marketplace inventory is not valid JSON"
                ) from error
            benchwork_marketplace = next(
                (
                    entry
                    for entry in marketplaces
                    if isinstance(entry, dict) and entry.get("name") == "benchwork-local"
                ),
                None,
            )
            expected = state["plugin"].get("marketplace_path")
            if benchwork_marketplace is not None:
                actual = benchwork_marketplace.get("root")
                if not isinstance(actual, str) or not isinstance(expected, str) or (
                    Path(actual).resolve() != Path(expected).resolve()
                ):
                    raise HostConfigurationError(
                        "refusing to remove a modified or non-installer-owned "
                        "benchwork-local marketplace"
                    )
            require_success(
                ["codex", "plugin", "remove", "benchwork@benchwork-local"],
                "Codex plugin removal",
            )
            if benchwork_marketplace is not None:
                require_success(
                    ["codex", "plugin", "marketplace", "remove", "benchwork-local"],
                    "Codex marketplace removal",
                )
        if codex["mcp"] == "configured" and not dry_run:
            require_success(
                ["codex", "mcp", "remove", "benchwork"],
                "Codex MCP removal",
            )
    claude = state["hosts"]["claude"]
    if _has_command("claude") and claude["mcp"] == "experimental" and not dry_run:
        require_success(
            ["claude", "mcp", "remove", "benchwork"],
            "Claude MCP removal",
        )
