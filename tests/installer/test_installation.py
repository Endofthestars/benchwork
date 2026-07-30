import hashlib
import io
import json
import os
import subprocess
import tarfile
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from benchwork.cli import main
from benchwork.install.manager import installation_plan
from benchwork.install.path import ensure_path_block, remove_path_block
from benchwork.install.plugin import (
    MAX_ARCHIVE_SIZE,
    extract_plugin_archive,
    install_plugin_archive,
    validate_plugin,
)
from benchwork.install.state import (
    InstallDocumentError,
    load_manifest,
    load_state,
    strict_json_bytes,
    write_state,
)


ROOT = Path(__file__).parents[2]
VERSION = "0.3.0rc2"
PLUGIN_VERSION = "0.3.0-rc.2"


def artifact(name: str, *, size: int = 1) -> dict:
    return {
        "url": f"https://example.test/{name}",
        "sha256": "0" * 64,
        "size": size,
    }


def manifest() -> dict:
    return {
        "schema_version": "benchwork-release-manifest/1.0",
        "version": VERSION,
        "tag": f"v{VERSION}",
        "channel": "rc",
        "python_requirement": ">=3.11",
        "package": {
            "name": "benchwork-arcana",
            "requirement": f"benchwork-arcana=={VERSION}",
            "wheel": artifact("benchwork.whl"),
            "sdist": artifact("benchwork.tar.gz"),
        },
        "plugin": {
            "name": "benchwork",
            "version": PLUGIN_VERSION,
            "runtime_requirement": f"benchwork-arcana=={VERSION}",
            "archive": artifact("plugin.tar.gz"),
        },
        "installer": artifact("install.sh"),
        "bootstrap": {
            "uv": {
                "version": "0.12.0",
                "installer": artifact("uv-install.sh"),
            }
        },
        "assets": {
            "sha256sums": artifact("SHA256SUMS"),
            "sbom": artifact("sbom.json"),
            "provenance": artifact("provenance.json"),
        },
    }


class InstallationDocumentTest(unittest.TestCase):
    def test_strict_json_rejects_duplicate_keys(self) -> None:
        with self.assertRaisesRegex(InstallDocumentError, "duplicate key"):
            strict_json_bytes(b'{"version":"one","version":"two"}', "fixture")

    def test_manifest_enforces_version_mapping(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "release-manifest.json"
            path.write_text(json.dumps(manifest()), encoding="utf-8")
            loaded = load_manifest(path)
            self.assertEqual(loaded["plugin"]["version"], PLUGIN_VERSION)

            invalid = manifest()
            invalid["plugin"]["version"] = "0.3.0-rc.1"
            path.write_text(json.dumps(invalid), encoding="utf-8")
            with self.assertRaisesRegex(InstallDocumentError, "does not match"):
                load_manifest(path)

    def test_state_write_is_atomic_and_validated(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            data = Path(directory) / "data"
            state_file = data / "install-state.json"
            state = {
                "schema_version": "benchwork-install-state/1.0",
                "installed_version": VERSION,
                "previous_version": None,
                "package_requirement": f"benchwork-arcana=={VERSION}",
                "manifest_url": f"https://example.test/releases/{VERSION}/release-manifest.json",
                "manifest_sha256": "a" * 64,
                "backend": "uv",
                "install_dir": str(data / "tools"),
                "bin_dir": str(data / "bin"),
                "bwork_path": str(data / "bin" / "bwork"),
                "backend_bootstrapped": True,
                "plugin": {
                    "scope": "none",
                    "version": None,
                    "path": None,
                    "marketplace_path": None,
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
            with patch.dict(os.environ, {"BENCHWORK_INSTALL_STATE": str(state_file)}):
                write_state(state)
                self.assertEqual(load_state(required=True), state)
                self.assertEqual(state_file.stat().st_mode & 0o777, 0o600)


class PluginArchiveTest(unittest.TestCase):
    def test_release_plugin_archive_installs_atomically(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "plugin.tar.gz"
            subprocess.run(
                [
                    "python3",
                    str(ROOT / "scripts" / "installer" / "build-plugin-archive.py"),
                    str(archive),
                ],
                check=True,
            )
            digest = hashlib.sha256(archive.read_bytes()).hexdigest()
            result = install_plugin_archive(
                archive,
                expected_sha256=digest,
                version=PLUGIN_VERSION,
                scope="user",
                data_root=root / "data",
            )
            installed = Path(result["path"])
            self.assertEqual(validate_plugin(installed, PLUGIN_VERSION)["skill_count"], 7)
            self.assertEqual(
                (root / "data" / "plugins" / "current").resolve(),
                installed.resolve(),
            )

    def test_archive_rejects_symlinks(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "malicious.tar.gz"
            with tarfile.open(archive, "w:gz") as bundle:
                link = tarfile.TarInfo("plugins/benchwork/escape")
                link.type = tarfile.SYMTYPE
                link.linkname = "../../outside"
                bundle.addfile(link)
            with self.assertRaisesRegex(InstallDocumentError, "not a regular file"):
                extract_plugin_archive(archive, root / "output")

    def test_archive_rejects_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "malicious.tar.gz"
            with tarfile.open(archive, "w:gz") as bundle:
                info = tarfile.TarInfo("../outside")
                info.size = 1
                bundle.addfile(info, io.BytesIO(b"x"))
            with self.assertRaisesRegex(InstallDocumentError, "unsafe archive path"):
                extract_plugin_archive(archive, root / "output")

    def test_archive_size_and_checksum_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            oversized = root / "oversized.tar.gz"
            with oversized.open("wb") as stream:
                stream.truncate(MAX_ARCHIVE_SIZE + 1)
            with self.assertRaisesRegex(InstallDocumentError, "size limit"):
                extract_plugin_archive(oversized, root / "output")
            archive = root / "plugin.tar.gz"
            subprocess.run(
                [
                    "python3",
                    str(ROOT / "scripts" / "installer" / "build-plugin-archive.py"),
                    str(archive),
                ],
                check=True,
            )
            with self.assertRaisesRegex(InstallDocumentError, "checksum mismatch"):
                install_plugin_archive(
                    archive,
                    expected_sha256="0" * 64,
                    version=PLUGIN_VERSION,
                    scope="user",
                    data_root=root / "data",
                )


class InstallationCommandTest(unittest.TestCase):
    def _run(self, *arguments: str) -> tuple[int, str]:
        output = io.StringIO()
        with redirect_stdout(output):
            code = main(arguments)
        return code, output.getvalue()

    def test_install_commands_do_not_require_a_project(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            previous = Path.cwd()
            os.chdir(directory)
            try:
                code, output = self._run("mcp", "check")
                self.assertEqual(code, 0)
                self.assertEqual(json.loads(output)["project_state"], "NOT_TOUCHED")
                self.assertFalse((Path(directory) / ".benchwork").exists())
            finally:
                os.chdir(previous)

    def test_plan_defaults_to_isolated_uv_without_mutation(self) -> None:
        with patch("benchwork.install.manager.shutil.which", return_value=None):
            plan = installation_plan(channel="rc")
        self.assertEqual(plan["backend"], "uv")
        self.assertTrue(plan["backend_bootstrap"])
        self.assertEqual(plan["project_state"], "NOT_TOUCHED")

    def test_path_block_is_idempotent_and_removable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            environment = {"HOME": str(home), "SHELL": "/bin/zsh", "XDG_DATA_HOME": str(home / "data")}
            with patch.dict(os.environ, environment, clear=False), patch(
                "pathlib.Path.home", return_value=home
            ):
                record, _ = ensure_path_block(home / ".local" / "bin")
                first = (home / ".zshrc").read_bytes()
                ensure_path_block(home / ".local" / "bin")
                self.assertEqual((home / ".zshrc").read_bytes(), first)
                remove_path_block(Path(record["path"]))
                self.assertNotIn("benchwork installer", (home / ".zshrc").read_text())
