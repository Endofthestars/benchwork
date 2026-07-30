import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

from benchwork.install import hosts
from benchwork.install.manager import (
    InstallationError,
    _download,
    configure_host,
    installation_doctor,
    installation_status,
    repair_installation,
    uninstall_installation,
)
from benchwork.install.path import ensure_path_block
from benchwork.install.path import remove_path_block
from benchwork.install.plugin import install_plugin_archive
from benchwork.install.state import (
    InstallDocumentError,
    load_state,
    reject_control_characters,
    strict_json_bytes,
    write_state,
)
from tests.installer.test_installation import PLUGIN_VERSION, ROOT, VERSION, manifest


def completed(
    arguments: list[str],
    returncode: int = 0,
    stdout: str = "",
    stderr: str = "",
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(arguments, returncode, stdout, stderr)


def state_document(root: Path, *, plugin_scope: str = "none") -> dict:
    plugin_path = root / "data" / "benchwork" / "plugins" / VERSION
    return {
        "schema_version": "benchwork-install-state/1.0",
        "installed_version": VERSION,
        "previous_version": None,
        "package_requirement": f"benchwork-arcana=={VERSION}",
        "manifest_url": f"https://example.test/releases/{VERSION}/release-manifest.json",
        "manifest_sha256": "a" * 64,
        "backend": "uv",
        "install_dir": str(root / "tools"),
        "bin_dir": str(root / "bin"),
        "bwork_path": str(root / "bin" / "bwork"),
        "backend_bootstrapped": True,
        "plugin": {
            "scope": plugin_scope,
            "version": PLUGIN_VERSION if plugin_scope != "none" else None,
            "path": str(plugin_path) if plugin_scope != "none" else None,
            "marketplace_path": str(plugin_path) if plugin_scope != "none" else None,
            "previous_path": None,
        },
        "hosts": {
            "codex": {"mcp": "not_configured", "plugin": "not_configured"},
            "claude": {"mcp": "not_configured", "plugin": "not_configured"},
        },
        "managed_files": [],
        "config_backups": [],
        "installed_at": "2026-07-30T00:00:00Z",
        "updated_at": "2026-07-30T00:00:00Z",
    }


def build_plugin_archive(root: Path) -> Path:
    archive = root / "plugin.tar.gz"
    subprocess.run(
        [
            "python3",
            str(ROOT / "scripts" / "installer" / "build-plugin-archive.py"),
            str(archive),
        ],
        check=True,
    )
    return archive


class StrictStateTest(unittest.TestCase):
    def test_strict_parser_and_control_character_failures(self) -> None:
        with self.assertRaisesRegex(InstallDocumentError, "not UTF-8"):
            strict_json_bytes(b"\xff")
        with self.assertRaisesRegex(InstallDocumentError, "invalid JSON"):
            strict_json_bytes(b"{")
        with self.assertRaisesRegex(InstallDocumentError, "JSON object"):
            strict_json_bytes(b"[]")
        with self.assertRaisesRegex(InstallDocumentError, "control character"):
            reject_control_characters("bad\npath", "path")

    def test_missing_required_state_is_actionable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            state_path = Path(directory) / "missing.json"
            with patch.dict(os.environ, {"BENCHWORK_INSTALL_STATE": str(state_path)}):
                with self.assertRaisesRegex(InstallDocumentError, "does not exist"):
                    load_state(required=True)


class PathManagementTest(unittest.TestCase):
    def test_fish_profile_dry_run_and_existing_backup(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            profile = root / ".config" / "fish" / "config.fish"
            profile.parent.mkdir(parents=True)
            profile.write_bytes(b"# existing\r\n")
            environment = {
                "HOME": str(root),
                "SHELL": "/usr/bin/fish",
                "XDG_DATA_HOME": str(root / "data"),
            }
            with patch.dict(os.environ, environment), patch(
                "pathlib.Path.home", return_value=root
            ):
                record, backup = ensure_path_block(root / "bin")
                self.assertEqual(record["kind"], "path_block")
                self.assertIsNotNone(backup)
                self.assertIn(b"set -gx PATH", profile.read_bytes())
                self.assertIn(b"\r\n", profile.read_bytes())
                before = profile.read_bytes()
                ensure_path_block(root / "other", dry_run=True)
                self.assertEqual(profile.read_bytes(), before)
                remove_path_block(profile)
                self.assertEqual(profile.read_bytes(), b"# existing\r\n")

    def test_unknown_shell_and_relative_path_fail(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.dict(os.environ, {"SHELL": "/bin/csh"}), patch(
                "pathlib.Path.home", return_value=root
            ):
                with self.assertRaisesRegex(InstallDocumentError, "cannot select"):
                    ensure_path_block(root / "bin")
            with self.assertRaisesRegex(InstallDocumentError, "absolute"):
                ensure_path_block(Path("relative"))


class HostConfigurationTest(unittest.TestCase):
    def test_codex_check_missing_and_detected(self) -> None:
        with patch("benchwork.install.hosts._has_command", return_value=False):
            self.assertFalse(hosts.codex_check()["detected"])
        results = [
            completed(["codex"], stdout="codex 1.2\n"),
            completed(["codex"], returncode=1),
            completed(["codex"], stdout="benchwork@benchwork-local\n"),
        ]
        with patch("benchwork.install.hosts._has_command", return_value=True), patch(
            "benchwork.install.hosts._run", side_effect=results
        ):
            status = hosts.codex_check()
        self.assertEqual(status["plugin"], "PASS")
        self.assertEqual(status["mcp"], "PASS")

    def test_codex_plugin_configuration_and_conflict(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            marketplace = home / "benchwork-marketplace"
            empty_marketplaces = json.dumps({"marketplaces": []})
            empty_plugins = json.dumps({"installed": []})
            with patch("pathlib.Path.home", return_value=home), patch(
                "benchwork.install.hosts._has_command", return_value=True
            ), patch(
                "benchwork.install.hosts._supports", return_value=True
            ), patch(
                "benchwork.install.hosts._run",
                side_effect=[
                    completed([], stdout=empty_marketplaces),
                    completed([], stdout=empty_plugins),
                    completed([]),
                    completed([]),
                ],
            ) as run:
                configured, backups = hosts.configure_codex(
                    marketplace,
                    expected_version=PLUGIN_VERSION,
                )
        self.assertEqual(configured["plugin"], "configured")
        self.assertEqual(backups, [])
        self.assertEqual(run.call_count, 4)

        conflict = json.dumps(
            {
                "marketplaces": [
                    {"name": "benchwork-local", "root": "/tmp/not-installer-owned"}
                ]
            }
        )
        with patch("benchwork.install.hosts._has_command", return_value=True), patch(
            "benchwork.install.hosts._supports", return_value=True
        ), patch(
            "benchwork.install.hosts._run",
            side_effect=[
                completed([], stdout=conflict),
                completed([], stdout=empty_plugins),
            ],
        ):
            with self.assertRaisesRegex(hosts.HostConfigurationError, "non-installer-owned"):
                hosts.configure_codex(marketplace, dry_run=True)

    def test_codex_mcp_fallback_and_claude_preview(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            with patch("pathlib.Path.home", return_value=home), patch(
                "benchwork.install.hosts._has_command", return_value=True
            ), patch(
                "benchwork.install.hosts._supports", return_value=False
            ), patch(
                "benchwork.install.hosts._run",
                side_effect=[completed([], returncode=1), completed([])],
            ):
                configured, _ = hosts.configure_codex(None)
            self.assertEqual(configured["mcp"], "configured")
            with patch("pathlib.Path.home", return_value=home), patch.dict(
                os.environ,
                {"XDG_DATA_HOME": str(home / "data")},
            ), patch("benchwork.install.hosts._has_command", return_value=True), patch(
                "benchwork.install.hosts._run",
                side_effect=[completed([], returncode=1), completed([])],
            ):
                configured, _ = hosts.configure_claude()
        self.assertEqual(configured["mcp"], "experimental")

    def test_host_failures_and_removal(self) -> None:
        with patch("benchwork.install.hosts._has_command", return_value=False):
            with self.assertRaisesRegex(hosts.HostConfigurationError, "not installed"):
                hosts.configure_codex(None)
            with self.assertRaisesRegex(hosts.HostConfigurationError, "not installed"):
                hosts.configure_claude()
            self.assertFalse(hosts.claude_check()["detected"])
        state = state_document(Path("/tmp/state"), plugin_scope="user")
        state["hosts"]["codex"] = {"mcp": "configured", "plugin": "configured"}
        state["hosts"]["claude"] = {"mcp": "experimental", "plugin": "not_configured"}

        def host_result(command):
            if command == ["codex", "plugin", "marketplace", "list", "--json"]:
                return completed(
                    command,
                    stdout=json.dumps(
                        {
                            "marketplaces": [
                                {
                                    "name": "benchwork-local",
                                    "root": state["plugin"]["marketplace_path"],
                                }
                            ]
                        }
                    ),
                )
            return completed(command)

        with patch("benchwork.install.hosts._has_command", return_value=True), patch(
            "benchwork.install.hosts._run", side_effect=host_result
        ) as run:
            hosts.remove_installer_owned_hosts(state)
        commands = [call.args[0] for call in run.call_args_list]
        self.assertIn(
            ["codex", "plugin", "remove", "benchwork@benchwork-local"],
            commands,
        )
        self.assertLess(
            commands.index(["codex", "plugin", "marketplace", "list", "--json"]),
            commands.index(["codex", "plugin", "remove", "benchwork@benchwork-local"]),
        )
        self.assertIn(["claude", "mcp", "remove", "benchwork"], commands)

        modified = completed(
            ["codex", "plugin", "marketplace", "list", "--json"],
            stdout=json.dumps(
                {
                    "marketplaces": [
                        {
                            "name": "benchwork-local",
                            "root": "/tmp/user-owned-marketplace",
                        }
                    ]
                }
            ),
        )
        with patch("benchwork.install.hosts._has_command", return_value=True), patch(
            "benchwork.install.hosts._run", return_value=modified
        ) as run:
            with self.assertRaisesRegex(
                hosts.HostConfigurationError,
                "refusing to remove",
            ):
                hosts.remove_installer_owned_hosts(state)
        run.assert_called_once_with(
            ["codex", "plugin", "marketplace", "list", "--json"]
        )

    def test_stale_codex_mcp_requires_force(self) -> None:
        stale = json.dumps(
            {
                "transport": {
                    "type": "stdio",
                    "command": "other",
                    "args": ["serve"],
                }
            }
        )
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            with patch("pathlib.Path.home", return_value=home), patch(
                "benchwork.install.hosts._has_command", return_value=True
            ), patch(
                "benchwork.install.hosts._supports", return_value=False
            ), patch(
                "benchwork.install.hosts._run",
                return_value=completed([], stdout=stale),
            ):
                with self.assertRaisesRegex(hosts.HostConfigurationError, "stale"):
                    hosts.configure_codex(None)
            with patch("pathlib.Path.home", return_value=home), patch(
                "benchwork.install.hosts._has_command", return_value=True
            ), patch(
                "benchwork.install.hosts._supports", return_value=False
            ), patch(
                "benchwork.install.hosts._run",
                side_effect=[
                    completed([], stdout=stale),
                    completed([]),
                    completed([]),
                ],
            ):
                configured, _ = hosts.configure_codex(None, force=True)
        self.assertEqual(configured["mcp"], "configured")


class ManagerLifecycleTest(unittest.TestCase):
    def test_status_and_doctor_without_installer_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            environment = {
                "BENCHWORK_INSTALL_STATE": str(root / "missing.json"),
                "XDG_DATA_HOME": str(root / "data"),
            }
            with patch.dict(os.environ, environment):
                self.assertFalse(installation_status()["installed"])
                with patch(
                    "benchwork.install.manager.shutil.which",
                    return_value=str(Path(sys.executable).with_name("bwork")),
                ):
                    doctor = installation_doctor()
        self.assertTrue(doctor["ok"])
        self.assertEqual(doctor["project_state"], "NOT_TOUCHED")

    def test_download_bounds_integrity_and_redirect_failures(self) -> None:
        with self.assertRaisesRegex(InstallationError, "HTTPS"):
            _download("http://example.test/file", 1, "0" * 64)
        with self.assertRaisesRegex(InstallationError, "bounds"):
            _download("https://example.test/file", 0, "0" * 64)

        class Response(io.BytesIO):
            def geturl(self) -> str:
                return "https://example.test/file"

            def __enter__(self):
                return self

            def __exit__(self, *arguments):
                self.close()

        payload = b"payload"
        digest = hashlib.sha256(payload).hexdigest()
        opener = type("Opener", (), {"open": lambda self, request, timeout: Response(payload)})()
        with patch("benchwork.install.manager.urllib.request.build_opener", return_value=opener):
            downloaded = _download("https://example.test/file", len(payload), digest)
        self.assertEqual(downloaded.read_bytes(), payload)
        downloaded.unlink()
        broken_opener = type(
            "BrokenOpener",
            (),
            {
                "open": lambda self, request, timeout: (_ for _ in ()).throw(
                    urllib.error.URLError("offline")
                )
            },
        )()
        with patch(
            "benchwork.install.manager.urllib.request.build_opener",
            return_value=broken_opener,
        ), patch("benchwork.install.manager.time.sleep"):
            with self.assertRaisesRegex(InstallationError, "download failed"):
                _download("https://example.test/file", len(payload), digest)

    def test_full_repair_is_idempotent_and_uninstall_removes_assets(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = build_plugin_archive(root)
            release = manifest()
            release["plugin"]["archive"]["size"] = archive.stat().st_size
            release["plugin"]["archive"]["sha256"] = hashlib.sha256(
                archive.read_bytes()
            ).hexdigest()
            manifest_path = root / "release-manifest.json"
            manifest_path.write_text(json.dumps(release), encoding="utf-8")
            state_file = root / "data" / "benchwork" / "install-state.json"
            environment = {
                "HOME": str(root / "home"),
                "XDG_DATA_HOME": str(root / "data"),
                "BENCHWORK_INSTALL_STATE": str(state_file),
                "SHELL": "/bin/zsh",
            }
            (root / "home").mkdir()
            with patch.dict(os.environ, environment), patch(
                "pathlib.Path.home", return_value=root / "home"
            ):
                result = repair_installation(
                    manifest_path=manifest_path,
                    manifest_url="https://example.test/release-manifest.json",
                    backend="uv",
                    install_dir=str(root / "tools"),
                    bin_dir=str(root / "bin"),
                    bwork_path=str(Path(sys.executable).with_name("bwork")),
                    backend_bootstrapped=True,
                    plugin_archive=archive,
                    plugin_scope="user",
                )
                self.assertEqual(result["status"], "PASS")
                installed = load_state(required=True)
                assert installed is not None
                plugin_base = Path(installed["plugin"]["path"]).parent
                self.assertTrue((plugin_base / "current").is_symlink())
                repair_installation(
                    manifest_path=manifest_path,
                    manifest_url="https://example.test/release-manifest.json",
                    backend="uv",
                    install_dir=str(root / "tools"),
                    bin_dir=str(root / "bin"),
                    bwork_path=str(Path(sys.executable).with_name("bwork")),
                    plugin_archive=archive,
                    plugin_scope="user",
                )
                repeated = load_state(required=True)
                assert repeated is not None
                managed_keys = [
                    (record["kind"], record["path"])
                    for record in repeated["managed_files"]
                ]
                self.assertEqual(len(managed_keys), len(set(managed_keys)))
                with patch(
                    "benchwork.install.manager.installation_doctor",
                    return_value={"ok": True},
                ):
                    second = repair_installation()
                self.assertFalse(second["changed"])
                with patch(
                    "benchwork.install.manager.shutil.which",
                    return_value="/fake/uv",
                ), patch(
                    "benchwork.install.manager.subprocess.run",
                    return_value=completed([]),
                ):
                    removed = uninstall_installation()
                self.assertEqual(removed["status"], "PASS")
                self.assertFalse(plugin_base.exists())
                self.assertFalse(state_file.exists())

    def test_repair_dry_run_and_host_configuration(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = root / "release-manifest.json"
            manifest_path.write_text(json.dumps(manifest()), encoding="utf-8")
            state_file = root / "state.json"
            environment = {
                "BENCHWORK_INSTALL_STATE": str(state_file),
                "XDG_DATA_HOME": str(root / "data"),
            }
            with patch.dict(os.environ, environment):
                result = repair_installation(
                    manifest_path=manifest_path,
                    backend="pipx",
                    install_dir=str(root / "pipx"),
                    bin_dir=str(root / "bin"),
                    bwork_path=str(root / "bin" / "bwork"),
                    dry_run=True,
                )
                self.assertFalse(result["changed"])
                self.assertFalse(state_file.exists())

                state = state_document(root)
                write_state(state)
                with patch(
                    "benchwork.install.manager.configure_codex",
                    return_value=(
                        {"mcp": "configured", "plugin": "unsupported"},
                        [],
                    ),
                ):
                    configured = configure_host("codex")
                self.assertEqual(configured["configuration"]["mcp"], "configured")
                with self.assertRaisesRegex(InstallationError, "unsupported Host"):
                    configure_host("other")

    def test_plugin_install_rolls_back_when_project_marketplace_write_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = build_plugin_archive(root)
            digest = hashlib.sha256(archive.read_bytes()).hexdigest()
            project = root / "project"
            project.mkdir()
            real_replace = os.replace
            failed = False

            def fail_once(source, destination):
                nonlocal failed
                if Path(destination).name == "marketplace.json" and not failed:
                    failed = True
                    raise OSError("injected marketplace failure")
                return real_replace(source, destination)

            with patch("benchwork.install.plugin.os.replace", side_effect=fail_once):
                with self.assertRaisesRegex(OSError, "injected"):
                    install_plugin_archive(
                        archive,
                        expected_sha256=digest,
                        version=PLUGIN_VERSION,
                        scope="project",
                        data_root=root / "data",
                        project_root=project,
                    )
            plugin_base = project / ".agents" / "benchwork-installer" / "plugins"
            self.assertFalse((plugin_base / "current").exists())
            self.assertFalse((plugin_base / PLUGIN_VERSION).exists())
            self.assertFalse(
                (project / ".agents" / "plugins" / "marketplace.json").exists()
            )

    def test_project_plugin_merge_and_manager_rollback_preserve_unrelated_config(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = build_plugin_archive(root)
            digest = hashlib.sha256(archive.read_bytes()).hexdigest()
            project = root / "project"
            marketplace_path = project / ".agents" / "plugins" / "marketplace.json"
            marketplace_path.parent.mkdir(parents=True)
            original = {
                "name": "benchwork-local",
                "interface": {"displayName": "Existing"},
                "plugins": [
                    {"name": "unrelated", "source": {"source": "local", "path": "./other"}},
                    {"name": "benchwork", "source": {"source": "local", "path": "./old"}},
                ],
            }
            marketplace_path.write_text(json.dumps(original), encoding="utf-8")
            environment = {
                "HOME": str(root / "home"),
                "XDG_DATA_HOME": str(root / "data"),
                "BENCHWORK_INSTALL_STATE": str(root / "state.json"),
            }
            (root / "home").mkdir()
            with patch.dict(os.environ, environment), patch(
                "pathlib.Path.home", return_value=root / "home"
            ):
                installed = install_plugin_archive(
                    archive,
                    expected_sha256=digest,
                    version=PLUGIN_VERSION,
                    scope="project",
                    data_root=root / "data",
                    project_root=project,
                )
                merged = json.loads(marketplace_path.read_text())
                self.assertEqual(
                    [entry["name"] for entry in merged["plugins"]],
                    ["unrelated", "benchwork"],
                )
                self.assertIsNotNone(installed["_marketplace_backup"])

                release = manifest()
                release["plugin"]["archive"]["size"] = archive.stat().st_size
                release["plugin"]["archive"]["sha256"] = digest
                manifest_path = root / "release-manifest.json"
                manifest_path.write_text(json.dumps(release), encoding="utf-8")
                before_failure = marketplace_path.read_bytes()
                with patch(
                    "benchwork.install.manager.configure_codex",
                    side_effect=hosts.HostConfigurationError("injected Host failure"),
                ):
                    with self.assertRaisesRegex(InstallationError, "injected Host"):
                        repair_installation(
                            manifest_path=manifest_path,
                            manifest_url="https://example.test/release-manifest.json",
                            backend="uv",
                            install_dir=str(root / "tools"),
                            bin_dir=str(root / "bin"),
                            bwork_path=str(Path(sys.executable).with_name("bwork")),
                            plugin_archive=archive,
                            plugin_scope="project",
                            project_root=project,
                            with_codex=True,
                        )
                self.assertEqual(marketplace_path.read_bytes(), before_failure)
                self.assertEqual(
                    (
                        project
                        / ".agents"
                        / "benchwork-installer"
                        / "plugins"
                        / "current"
                    ).resolve(),
                    Path(installed["path"]),
                )

    def test_repair_configures_hosts_path_and_project_uninstall(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = root / "home"
            home.mkdir()
            archive = build_plugin_archive(root)
            digest = hashlib.sha256(archive.read_bytes()).hexdigest()
            release = manifest()
            release["plugin"]["archive"]["size"] = archive.stat().st_size
            release["plugin"]["archive"]["sha256"] = digest
            manifest_path = root / "release-manifest.json"
            manifest_path.write_text(json.dumps(release), encoding="utf-8")
            project = root / "project"
            project.mkdir()
            state_file = root / "data" / "benchwork" / "install-state.json"
            environment = {
                "HOME": str(home),
                "SHELL": "/bin/zsh",
                "XDG_DATA_HOME": str(root / "data"),
                "BENCHWORK_INSTALL_STATE": str(state_file),
            }
            with patch.dict(os.environ, environment), patch(
                "pathlib.Path.home", return_value=home
            ), patch(
                "benchwork.install.manager.configure_codex",
                return_value=(
                    {"mcp": "plugin_managed", "plugin": "configured"},
                    [],
                ),
            ), patch(
                "benchwork.install.manager.configure_claude",
                return_value=(
                    {"mcp": "experimental", "plugin": "not_configured"},
                    [],
                ),
            ), patch(
                "benchwork.install.manager.mcp_check",
                return_value={"status": "PASS"},
            ), patch(
                "benchwork.install.manager.codex_check",
                return_value={"mcp": "PASS", "plugin": "PASS"},
            ), patch(
                "benchwork.install.manager.claude_check",
                return_value={"mcp": "EXPERIMENTAL"},
            ):
                result = repair_installation(
                    manifest_path=manifest_path,
                    manifest_url="https://example.test/release-manifest.json",
                    backend="pipx",
                    install_dir=str(root / "pipx"),
                    bin_dir=str(root / "bin"),
                    bwork_path=str(Path(sys.executable).with_name("bwork")),
                    plugin_archive=archive,
                    plugin_scope="project",
                    project_root=project,
                    with_codex=True,
                    with_claude=True,
                    modify_path=True,
                )
                self.assertEqual(result["hosts"]["codex"]["plugin"], "configured")
                self.assertIn("benchwork installer", (home / ".zshrc").read_text())
                with patch(
                    "benchwork.install.manager.configure_claude",
                    return_value=(
                        {"mcp": "experimental", "plugin": "not_configured"},
                        [],
                    ),
                ):
                    preview = configure_host("claude", dry_run=True)
                self.assertFalse(preview["changed"])
                with patch(
                    "benchwork.install.manager.remove_installer_owned_hosts"
                ), patch(
                    "benchwork.install.manager.shutil.which",
                    return_value="/fake/pipx",
                ), patch(
                    "benchwork.install.manager.subprocess.run",
                    return_value=completed([]),
                ):
                    removed = uninstall_installation(purge=True)
                self.assertEqual(removed["status"], "PASS")
                self.assertNotIn("benchwork installer", (home / ".zshrc").read_text())
                marketplace_path = project / ".agents" / "plugins" / "marketplace.json"
                self.assertFalse(marketplace_path.exists())
                self.assertFalse(
                    (project / ".agents" / "benchwork-installer" / "plugins").exists()
                )


if __name__ == "__main__":
    unittest.main()
