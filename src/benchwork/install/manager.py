"""High-level installation diagnostics, configuration, repair, and removal."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from importlib.resources import files
from pathlib import Path
from typing import Any

from .. import __version__
from ..mcp.tool_registry import load_tool_registry
from ..schema_validation import _schema_directory
from .hosts import (
    HostConfigurationError,
    claude_check,
    codex_check,
    configure_claude,
    configure_codex,
    remove_installer_owned_hosts,
)
from .path import ensure_path_block, remove_path_block
from .plugin import install_plugin_archive, validate_plugin
from .state import (
    InstallDocumentError,
    installer_data_root,
    load_manifest,
    load_state,
    sha256_file,
    state_path,
    strict_json_file,
    write_state,
)


class InstallationError(ValueError):
    """Stable installer failure with an actionable message."""


class _BoundedRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Reject long redirect chains and HTTPS downgrades."""

    max_redirections = 3

    def redirect_request(
        self,
        request: urllib.request.Request,
        file_pointer: Any,
        code: int,
        message: str,
        headers: Any,
        new_url: str,
    ) -> urllib.request.Request | None:
        if not new_url.startswith("https://"):
            raise InstallationError("artifact redirected to a non-HTTPS URL")
        return super().redirect_request(
            request,
            file_pointer,
            code,
            message,
            headers,
            new_url,
        )


def _translate(error: ValueError) -> InstallationError:
    return InstallationError(str(error))


def installation_plan(
    *,
    version: str | None = None,
    channel: str = "stable",
    backend: str = "auto",
    install_dir: str | None = None,
    bin_dir: str | None = None,
    plugin_scope: str = "none",
    project_root: str | None = None,
    with_codex: bool = False,
    with_claude: bool = False,
    modify_path: bool = False,
) -> dict[str, Any]:
    selected_backend = backend
    if backend == "auto":
        selected_backend = (
            "uv" if shutil.which("uv") else "pipx" if shutil.which("pipx") else "uv"
        )
    default_bin = Path.home() / ".local" / "bin"
    return {
        "schema_version": "benchwork-install-plan/1.0",
        "version": version,
        "channel": None if version else channel,
        "backend": selected_backend,
        "backend_bootstrap": selected_backend == "uv" and shutil.which("uv") is None,
        "install_dir": install_dir,
        "bin_dir": str(Path(bin_dir).expanduser() if bin_dir else default_bin),
        "plugin_scope": plugin_scope,
        "project_root": project_root,
        "hosts": {
            "codex": {
                "requested": with_codex,
                "detected": shutil.which("codex") is not None,
            },
            "claude": {
                "requested": with_claude,
                "detected": shutil.which("claude") is not None,
                "support": "experimental_mcp_only",
            },
        },
        "modify_path": modify_path,
        "persistent_changes": [
            "isolated backend tool environment",
            *([] if plugin_scope == "none" else ["versioned plugin marketplace"]),
            *([] if not with_codex else ["Codex configuration"]),
            *([] if not with_claude else ["Claude MCP configuration"]),
            *([] if not modify_path else ["one managed shell-profile PATH block"]),
            "installer-owned state outside research projects",
        ],
        "project_state": "NOT_TOUCHED",
        "rollback": "bwork install uninstall",
    }


def installation_status() -> dict[str, Any]:
    try:
        state = load_state()
    except ValueError as error:
        raise _translate(error) from error
    if state is None:
        return {
            "installed": False,
            "version": __version__,
            "state_path": str(state_path()),
            "action": "Run the Benchwork installer or bwork install doctor.",
        }
    return {
        "installed": True,
        "version": state["installed_version"],
        "backend": state["backend"],
        "bwork_path": state["bwork_path"],
        "plugin": state["plugin"],
        "hosts": state["hosts"],
        "state_path": str(state_path()),
    }


def mcp_check() -> dict[str, Any]:
    registry = load_tool_registry()
    requests = "\n".join(
        (
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {"protocolVersion": "2025-11-25"},
                }
            ),
            json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}),
            "",
        )
    )
    try:
        result = subprocess.run(
            [sys.executable, "-m", "benchwork.mcp.server"],
            input=requests,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        responses = [json.loads(line) for line in result.stdout.splitlines() if line]
        initialized = (
            result.returncode == 0
            and len(responses) == 2
            and responses[0].get("result", {}).get("serverInfo", {}).get("version")
            == __version__
        )
        listed = len(responses[1].get("result", {}).get("tools", [])) if len(responses) > 1 else 0
        running = initialized and listed == len(registry["tools"])
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
        running = False
        listed = 0
    return {
        "status": "PASS" if running else "FAIL",
        "registry": registry["schema_version"],
        "tool_count": len(registry["tools"]),
        "server_started": running,
        "server_tool_count": listed,
        "project_state": "NOT_TOUCHED",
    }


def plugin_check() -> dict[str, Any]:
    try:
        state = load_state()
        if state is None or state["plugin"]["scope"] == "none":
            return {
                "status": "NOT_CONFIGURED",
                "action": "Rerun with --plugin-scope user or --with-codex.",
            }
        path_value = state["plugin"]["path"]
        if not isinstance(path_value, str):
            raise InstallDocumentError("installer state has no plugin path")
        result = validate_plugin(Path(path_value), state["plugin"]["version"])
        return {"status": "PASS", **result}
    except ValueError as error:
        return {"status": "FAIL", "error": str(error), "action": "Run bwork install repair."}


def host_check(host: str) -> dict[str, Any]:
    if host == "codex":
        return codex_check()
    if host == "claude":
        return claude_check()
    raise InstallationError(f"unsupported Host: {host}")


def installation_doctor() -> dict[str, Any]:
    checks: dict[str, Any] = {}
    checks["version"] = {
        "status": "PASS",
        "installed": __version__,
    }
    try:
        schema_dir = _schema_directory()
        schema_count = len(list(schema_dir.glob("*.json")))
        checks["schemas"] = {
            "status": "PASS" if schema_count else "FAIL",
            "path": str(schema_dir),
            "count": schema_count,
        }
    except ValueError as error:
        checks["schemas"] = {"status": "FAIL", "error": str(error)}
    registry = load_tool_registry()
    checks["mcp_registry"] = {
        "status": "PASS",
        "schema": registry["schema_version"],
        "count": len(registry["tools"]),
    }
    compatibility = json.loads(
        files("benchwork.install").joinpath("compatibility.json").read_text(encoding="utf-8")
    )
    checks["compatibility"] = {
        "status": "PASS" if compatibility["version"] == __version__ else "FAIL",
        **compatibility,
    }
    try:
        state = load_state()
    except ValueError as error:
        state = None
        checks["installer_state"] = {"status": "FAIL", "error": str(error)}
    expected = (
        Path(state["bwork_path"]).expanduser()
        if state is not None
        else None
    )
    resolved = shutil.which("bwork")
    executable_path = (
        expected
        if expected is not None and expected.is_file() and os.access(expected, os.X_OK)
        else Path(resolved) if resolved else None
    )
    expected_matches = (
        expected is None
        or executable_path is not None
        and executable_path.resolve() == expected.resolve()
    )
    on_path = resolved is not None and (
        expected is None or Path(resolved).resolve() == expected.resolve()
    )
    checks["executable"] = {
        "status": "PASS" if executable_path is not None and expected_matches else "FAIL",
        "path": str(executable_path) if executable_path is not None else None,
        "expected": str(expected) if expected is not None else None,
        "on_path": on_path,
    }
    checks["mcp_server"] = mcp_check()
    checks["plugin"] = plugin_check()
    checks["codex"] = codex_check()
    checks["claude"] = claude_check()
    required = ("version", "schemas", "mcp_registry", "compatibility", "executable", "mcp_server")
    ok = all(checks[name]["status"] == "PASS" for name in required)
    return {
        "ok": ok,
        "checks": checks,
        "project_state": "NOT_TOUCHED",
        "action": "No action required." if ok else "Run bwork install repair.",
    }


def _download(url: str, expected_size: int, expected_sha256: str) -> Path:
    if not url.startswith("https://"):
        raise InstallationError("artifact URL must use HTTPS")
    if expected_size <= 0 or expected_size > 25 * 1024 * 1024:
        raise InstallationError("artifact size is outside installer bounds")
    request = urllib.request.Request(url, headers={"User-Agent": "benchwork-installer/0.3"})
    response = None
    last_error: urllib.error.URLError | TimeoutError | None = None
    for attempt in range(3):
        try:
            response = urllib.request.build_opener(_BoundedRedirectHandler()).open(
                request,
                timeout=30,
            )
            break
        except (urllib.error.URLError, TimeoutError) as error:
            last_error = error
            if attempt < 2:
                time.sleep(2**attempt)
    if response is None:
        raise InstallationError(f"artifact download failed: {last_error}") from last_error
    final_url = response.geturl()
    if not final_url.startswith("https://"):
        response.close()
        raise InstallationError("artifact redirected to a non-HTTPS URL")
    descriptor, name = tempfile.mkstemp(prefix="benchwork-artifact-")
    received = 0
    try:
        with os.fdopen(descriptor, "wb") as output, response:
            while True:
                chunk = response.read(min(1024 * 1024, expected_size + 1 - received))
                if not chunk:
                    break
                received += len(chunk)
                if received > expected_size:
                    raise InstallationError("artifact exceeds its manifest size")
                output.write(chunk)
        path = Path(name)
        if received != expected_size:
            raise InstallationError("artifact size does not match manifest")
        if sha256_file(path) != expected_sha256:
            raise InstallationError("artifact checksum does not match manifest")
        return path
    except BaseException:
        Path(name).unlink(missing_ok=True)
        raise


def _empty_hosts() -> dict[str, dict[str, str]]:
    return {
        "codex": {"mcp": "not_configured", "plugin": "not_configured"},
        "claude": {"mcp": "not_configured", "plugin": "not_configured"},
    }


def _shell_quote(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"


def _write_uninstaller(
    *,
    backend: str,
    install_dir: str,
    bwork_path: str,
) -> dict[str, Any]:
    path = installer_data_root() / "uninstall.sh"
    candidates = [bwork_path]
    if backend == "uv":
        candidates.append(str(Path(install_dir) / "benchwork-arcana" / "bin" / "bwork"))
    else:
        candidates.append(
            str(Path(install_dir) / "venvs" / "benchwork-arcana" / "bin" / "bwork")
        )
    lines = [
        "#!/bin/sh",
        "set -eu",
        *[
            f"if [ -x {_shell_quote(candidate)} ]; then "
            f"exec {_shell_quote(candidate)} install uninstall \"$@\"; fi"
            for candidate in candidates
        ],
        'printf "%s\\n" "Benchwork executable is unavailable; rerun the public installer with --repair." >&2',
        "exit 5",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.write_text("\n".join(lines), encoding="utf-8")
    path.chmod(0o700)
    return {"path": str(path), "kind": "script", "sha256": sha256_file(path)}


def repair_installation(
    *,
    manifest_path: Path | None = None,
    manifest_url: str | None = None,
    manifest_sha256: str | None = None,
    backend: str | None = None,
    install_dir: str | None = None,
    bin_dir: str | None = None,
    bwork_path: str | None = None,
    backend_bootstrapped: bool = False,
    plugin_archive: Path | None = None,
    plugin_scope: str = "none",
    project_root: Path | None = None,
    with_codex: bool = False,
    with_claude: bool = False,
    modify_path: bool = False,
    dry_run: bool = False,
    force: bool = False,
) -> dict[str, Any]:
    downloaded: Path | None = None
    changed_plugin: dict[str, Any] | None = None
    changed_plugin_current: str | None = None
    changed_marketplace_file: str | None = None
    changed_marketplace_backup: dict[str, str] | None = None
    operation_backups: list[dict[str, str]] = []
    try:
        existing = load_state()
        if manifest_path is None:
            if existing is None:
                raise InstallDocumentError(
                    "repair requires installer state or an explicit release manifest"
                )
            doctor = installation_doctor()
            if doctor["ok"]:
                return {
                    "status": "PASS",
                    "changed": False,
                    "version": existing["installed_version"],
                    "project_state": "NOT_TOUCHED",
                }
            raise InstallDocumentError(
                "installation is unhealthy; rerun the public installer with --repair"
            )

        manifest = load_manifest(manifest_path)
        version = manifest["version"]
        if version != __version__:
            raise InstallDocumentError(
                f"installed CLI {__version__} does not match requested release {version}"
            )
        manifest_digest = sha256_file(manifest_path)
        if manifest_sha256 is not None and manifest_digest != manifest_sha256:
            raise InstallDocumentError("release manifest checksum mismatch")
        recorded_manifest_url = manifest_url or (
            existing["manifest_url"] if existing is not None else None
        )
        if recorded_manifest_url is None and not dry_run:
            raise InstallDocumentError(
                "applying a release manifest requires its immutable HTTPS --manifest-url"
            )
        archive = plugin_archive
        if plugin_scope != "none" and archive is None and not dry_run:
            artifact = manifest["plugin"]["archive"]
            downloaded = _download(artifact["url"], artifact["size"], artifact["sha256"])
            archive = downloaded
        now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        hosts = existing["hosts"] if existing else _empty_hosts()
        backups = list(existing["config_backups"]) if existing else []
        original_backup_count = len(backups)
        managed = list(existing["managed_files"]) if existing else []
        plugin = (
            existing["plugin"]
            if existing and plugin_scope == "none"
            else {
                "scope": "none",
                "version": None,
                "path": None,
                "marketplace_path": None,
                "previous_path": None,
            }
        )
        if archive is not None and not dry_run:
            plugin = install_plugin_archive(
                archive,
                expected_sha256=manifest["plugin"]["archive"]["sha256"],
                version=manifest["plugin"]["version"],
                scope=plugin_scope,
                data_root=installer_data_root(),
                project_root=project_root,
            )
            marketplace_file = plugin.pop("_marketplace_file", None)
            marketplace_sha256 = plugin.pop("_marketplace_sha256", None)
            marketplace_backup = plugin.pop("_marketplace_backup", None)
            changed_plugin_current = plugin.pop("_rollback_current_path", None)
            changed_plugin = plugin
            changed_marketplace_file = marketplace_file
            changed_marketplace_backup = marketplace_backup
            if plugin["path"]:
                managed.append(
                    {"path": plugin["path"], "kind": "plugin", "sha256": None}
                )
            if marketplace_file:
                managed.append(
                    {
                        "path": marketplace_file,
                        "kind": "marketplace",
                        "sha256": marketplace_sha256,
                    }
                )
            if marketplace_backup:
                backups.append(marketplace_backup)
        marketplace_value = plugin.get("marketplace_path")
        marketplace = Path(marketplace_value) if isinstance(marketplace_value, str) else None
        if with_codex:
            previous_marketplace = None
            if existing and isinstance(existing["plugin"].get("marketplace_path"), str):
                previous_marketplace = Path(existing["plugin"]["marketplace_path"])
            host_state, host_backups = configure_codex(
                marketplace,
                expected_version=manifest["plugin"]["version"],
                previous_marketplace=previous_marketplace,
                force=force,
                dry_run=dry_run,
            )
            hosts["codex"] = host_state
            backups.extend(host_backups)
        if with_claude:
            host_state, host_backups = configure_claude(dry_run=dry_run)
            hosts["claude"] = host_state
            backups.extend(host_backups)
        if modify_path:
            selected_bin = Path(bin_dir or (Path.home() / ".local" / "bin")).expanduser()
            record, backup = ensure_path_block(selected_bin, dry_run=dry_run)
            managed.append(record)
            if backup is not None:
                backups.append(backup)
        operation_backups = backups[original_backup_count:]
        managed = list(
            {
                (record["kind"], record["path"]): record
                for record in managed
            }.values()
        )
        backups = list(
            {
                record["backup"]: record
                for record in backups
            }.values()
        )
        if not dry_run:
            mcp_result = mcp_check()
            if mcp_result["status"] != "PASS":
                raise HostConfigurationError("MCP startup verification failed after configuration")
            if with_codex:
                codex_result = codex_check()
                if codex_result["mcp"] != "PASS":
                    raise HostConfigurationError("Codex MCP verification failed after configuration")
                if marketplace is not None and codex_result["plugin"] != "PASS":
                    raise HostConfigurationError(
                        "Codex plugin verification failed after configuration"
                    )
            if with_claude and claude_check()["mcp"] != "EXPERIMENTAL":
                raise HostConfigurationError("Claude MCP verification failed after configuration")
        state = {
            "schema_version": "benchwork-install-state/1.0",
            "installed_version": version,
            "previous_version": (
                existing["installed_version"]
                if existing and existing["installed_version"] != version
                else existing.get("previous_version") if existing else None
            ),
            "package_requirement": manifest["package"]["requirement"],
            "manifest_url": recorded_manifest_url or manifest["installer"]["url"],
            "manifest_sha256": manifest_digest,
            "backend": backend or (existing["backend"] if existing else "uv"),
            "install_dir": install_dir or (existing["install_dir"] if existing else ""),
            "bin_dir": bin_dir or (existing["bin_dir"] if existing else str(Path.home() / ".local" / "bin")),
            "bwork_path": bwork_path or shutil.which("bwork") or str(Path.home() / ".local" / "bin" / "bwork"),
            "backend_bootstrapped": backend_bootstrapped or bool(existing and existing["backend_bootstrapped"]),
            "plugin": plugin,
            "hosts": hosts,
            "managed_files": managed,
            "config_backups": backups,
            "installed_at": existing["installed_at"] if existing else now,
            "updated_at": now,
        }
        if not dry_run:
            managed = [
                record
                for record in managed
                if not (record["kind"] == "script" and record["path"].endswith("/uninstall.sh"))
            ]
            managed.append(
                _write_uninstaller(
                    backend=state["backend"],
                    install_dir=state["install_dir"],
                    bwork_path=state["bwork_path"],
                )
            )
            state["managed_files"] = managed
            write_state(state)
        return {
            "status": "PASS",
            "changed": not dry_run,
            "version": version,
            "plugin": plugin,
            "hosts": hosts,
            "state_path": str(state_path()),
            "project_state": "NOT_TOUCHED",
        }
    except (InstallDocumentError, HostConfigurationError) as error:
        if not dry_run:
            for backup in reversed(operation_backups):
                source = Path(backup["source"])
                backup_path = Path(backup["backup"])
                if backup_path.is_file():
                    source.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(backup_path, source)
        if not dry_run and changed_plugin is not None:
            installed_path = changed_plugin.get("path")
            previous_path = changed_plugin_current or changed_plugin.get("previous_path")
            if isinstance(installed_path, str):
                current = Path(installed_path).parent / "current"
                pointer = current.with_name(f".rollback-current-{os.getpid()}")
                try:
                    if isinstance(previous_path, str):
                        pointer.symlink_to(
                            Path(previous_path).name,
                            target_is_directory=True,
                        )
                        os.replace(pointer, current)
                    else:
                        current.unlink(missing_ok=True)
                finally:
                    pointer.unlink(missing_ok=True)
                if not isinstance(previous_path, str) or Path(previous_path) != Path(
                    installed_path
                ):
                    shutil.rmtree(installed_path, ignore_errors=True)
            if changed_marketplace_file is not None:
                marketplace_path = Path(changed_marketplace_file)
                if changed_marketplace_backup is not None:
                    shutil.copy2(
                        changed_marketplace_backup["backup"],
                        marketplace_path,
                    )
                else:
                    marketplace_path.unlink(missing_ok=True)
        raise _translate(error) from error
    finally:
        if downloaded is not None:
            downloaded.unlink(missing_ok=True)


def configure_host(host: str, *, dry_run: bool = False) -> dict[str, Any]:
    try:
        state = load_state(required=True)
        assert state is not None
        marketplace = (
            Path(state["plugin"]["marketplace_path"])
            if isinstance(state["plugin"]["marketplace_path"], str)
            else None
        )
        if host == "codex":
            result, backups = configure_codex(
                marketplace,
                expected_version=state["plugin"]["version"],
                previous_marketplace=marketplace,
                dry_run=dry_run,
            )
        elif host == "claude":
            result, backups = configure_claude(dry_run=dry_run)
        else:
            raise InstallationError(f"unsupported Host: {host}")
        if not dry_run:
            state["hosts"][host] = result
            state["config_backups"].extend(backups)
            state["updated_at"] = datetime.now(UTC).isoformat().replace("+00:00", "Z")
            write_state(state)
        return {
            "status": "PASS",
            "host": host,
            "configuration": result,
            "changed": not dry_run,
        }
    except (InstallDocumentError, HostConfigurationError) as error:
        raise _translate(error) from error


def _remove_project_marketplace_entry(path: Path) -> None:
    document = strict_json_file(path, "project Codex marketplace")
    plugins = document.get("plugins")
    if not isinstance(plugins, list):
        raise InstallDocumentError("project marketplace plugins must be an array")
    retained = [
        entry
        for entry in plugins
        if not isinstance(entry, dict) or entry.get("name") != "benchwork"
    ]
    if len(retained) == len(plugins):
        return
    if not retained and document.get("name") == "benchwork-local":
        path.unlink()
        return
    document["plugins"] = retained
    temporary = path.with_name(f".marketplace-uninstall-{os.getpid()}.json")
    temporary.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def uninstall_installation(*, dry_run: bool = False, purge: bool = False) -> dict[str, Any]:
    try:
        state = load_state(required=True)
        assert state is not None
        project_root = (
            Path(state["plugin"]["marketplace_path"])
            if state["plugin"]["scope"] == "project"
            and isinstance(state["plugin"]["marketplace_path"], str)
            else None
        )
        recorded_plugin_path = (
            Path(state["plugin"]["path"])
            if isinstance(state["plugin"]["path"], str)
            else None
        )
        plugin_path = state["plugin"]["path"]
        data_root = installer_data_root().resolve()

        def project_owned_record(record: dict[str, Any], path: Path) -> bool:
            return not path.is_symlink() and project_root is not None and (
                record["kind"] == "marketplace"
                and path == project_root / ".agents" / "plugins" / "marketplace.json"
                or record["kind"] == "plugin"
                and recorded_plugin_path is not None
                and path == recorded_plugin_path
            )

        if not dry_run:
            codex_state = state["hosts"]["codex"]
            if (
                codex_state["plugin"] == "configured"
                or codex_state["mcp"] == "configured"
            ) and not shutil.which("codex"):
                raise InstallDocumentError(
                    "Codex is unavailable; reinstall it or remove the installer-owned "
                    "Benchwork entries before uninstall"
                )
            if (
                state["hosts"]["claude"]["mcp"] == "experimental"
                and not shutil.which("claude")
            ):
                raise InstallDocumentError(
                    "Claude Code is unavailable; reinstall it or remove the "
                    "installer-owned Benchwork MCP entry before uninstall"
                )
            for record in state["managed_files"]:
                path = Path(record["path"])
                if (
                    record["kind"] in {"plugin", "marketplace", "script"}
                    and path.exists()
                    and data_root not in path.resolve().parents
                    and not project_owned_record(record, path)
                ):
                    raise InstallDocumentError(
                        f"refusing to remove path outside installer ownership: {path}"
                    )
            if isinstance(plugin_path, str):
                plugin_base = Path(plugin_path).parent
                project_owned = (
                    not plugin_base.is_symlink()
                    and project_root is not None
                    and plugin_base
                    == project_root / ".agents" / "benchwork-installer" / "plugins"
                )
                if data_root not in plugin_base.resolve().parents and not project_owned:
                    raise InstallDocumentError(
                        "refusing to remove plugin directory outside installer ownership: "
                        f"{plugin_base}"
                    )

        backend = state["backend"]
        command = (
            ["uv", "tool", "uninstall", "benchwork-arcana"]
            if backend == "uv"
            else ["pipx", "uninstall", "benchwork-arcana"]
        )
        if not dry_run:
            if not shutil.which(command[0]):
                raise InstallDocumentError(
                    f"recorded {backend} backend is unavailable; reinstall it and retry uninstall"
                )
            backend_environment = dict(os.environ)
            if backend == "uv":
                backend_environment.update(
                    {
                        "UV_TOOL_DIR": state["install_dir"],
                        "UV_TOOL_BIN_DIR": state["bin_dir"],
                    }
                )
            else:
                backend_environment.update(
                    {
                        "PIPX_HOME": state["install_dir"],
                        "PIPX_BIN_DIR": state["bin_dir"],
                    }
                )
            removal = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
                timeout=60,
                env=backend_environment,
            )
            if removal.returncode != 0:
                raise InstallDocumentError(
                    f"{backend} could not remove Benchwork: "
                    f"{(removal.stderr or removal.stdout).strip()}"
                )

        remove_installer_owned_hosts(state, dry_run=dry_run)
        for record in state["managed_files"]:
            path = Path(record["path"])
            if record["kind"] == "path_block":
                remove_path_block(path, dry_run=dry_run)
            elif record["kind"] in {"plugin", "marketplace", "script"}:
                if not dry_run and path.exists():
                    if record["kind"] == "marketplace":
                        _remove_project_marketplace_entry(path)
                    elif path.is_dir():
                        shutil.rmtree(path)
                    else:
                        path.unlink()
        plugin_path = state["plugin"]["path"]
        if not dry_run and isinstance(plugin_path, str):
            plugin_base = Path(plugin_path).parent
            shutil.rmtree(plugin_base, ignore_errors=True)
        if not dry_run:
            state_path().unlink(missing_ok=True)
            if purge:
                shutil.rmtree(installer_data_root() / "backups", ignore_errors=True)
        return {
            "status": "PASS",
            "changed": not dry_run,
            "preserved": ["all research projects", *([] if purge else ["configuration backups"])],
            "project_state": "NOT_TOUCHED",
        }
    except (InstallDocumentError, HostConfigurationError) as error:
        raise _translate(error) from error
