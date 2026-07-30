import json
import os
import hashlib
import shlex
import subprocess
import tempfile
import unittest
from pathlib import Path

from tests.installer.test_installation import manifest


ROOT = Path(__file__).parents[2]


def run_exact_dry(document: str) -> subprocess.CompletedProcess[str]:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        home = root / "home"
        work = root / "work"
        fake_bin = root / "bin"
        home.mkdir()
        work.mkdir()
        fake_bin.mkdir()
        manifest_path = root / "release-manifest.json"
        manifest_path.write_text(document, encoding="utf-8")
        fake_curl = fake_bin / "curl"
        fake_curl.write_text(
            """#!/usr/bin/python3
import os, shutil, sys
args = sys.argv[1:]
output = args[args.index("--output") + 1]
shutil.copyfile(os.environ["FAKE_MANIFEST"], output)
""",
            encoding="utf-8",
        )
        fake_curl.chmod(0o755)
        environment = {
            **os.environ,
            "HOME": str(home),
            "PATH": f"{fake_bin}:/usr/bin:/bin",
            "FAKE_MANIFEST": str(manifest_path),
            "BENCHWORK_INSTALLER_BASE_URL": "https://example.test",
        }
        result = subprocess.run(
            [
                "sh",
                str(ROOT / "install.sh"),
                "--dry-run",
                "--json",
                "--version",
                "0.3.0rc2",
            ],
            cwd=work,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            self_state = home / ".local" / "share" / "benchwork"
            if self_state.exists():
                raise AssertionError("failing dry run mutated installer state")
        return result


class InstallerShellTest(unittest.TestCase):
    def test_help_and_unknown_option(self) -> None:
        help_result = subprocess.run(
            ["sh", str(ROOT / "install.sh"), "--help"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(help_result.returncode, 0)
        self.assertIn("--plugin-scope", help_result.stdout)
        invalid = subprocess.run(
            ["sh", str(ROOT / "install.sh"), "--unknown"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(invalid.returncode, 2)
        self.assertIn("unknown option", invalid.stderr)

    def test_exact_dry_run_is_non_mutating(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = root / "home"
            work = root / "work"
            fake_bin = root / "bin"
            home.mkdir()
            work.mkdir()
            fake_bin.mkdir()
            manifest_path = root / "release-manifest.json"
            manifest_path.write_text(json.dumps(manifest()), encoding="utf-8")
            fake_curl = fake_bin / "curl"
            fake_curl.write_text(
                """#!/usr/bin/python3
import os, pathlib, shutil, sys
args = sys.argv[1:]
output = args[args.index("--output") + 1]
shutil.copyfile(os.environ["FAKE_MANIFEST"], output)
""",
                encoding="utf-8",
            )
            fake_curl.chmod(0o755)
            environment = {
                **os.environ,
                "HOME": str(home),
                "PATH": f"{fake_bin}:/usr/bin:/bin",
                "FAKE_MANIFEST": str(manifest_path),
                "BENCHWORK_INSTALLER_BASE_URL": "https://example.test",
            }
            result = subprocess.run(
                [
                    "sh",
                    str(ROOT / "install.sh"),
                    "--dry-run",
                    "--json",
                    "--version",
                    "0.3.0rc2",
                ],
                cwd=work,
                env=environment,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["project_state"], "NOT_TOUCHED")
            self.assertFalse((work / ".benchwork").exists())
            self.assertFalse((home / ".local" / "share" / "benchwork").exists())

    def test_manifest_mismatches_and_duplicate_keys_fail_before_mutation(self) -> None:
        invalid = manifest()
        invalid["tag"] = "v0.3.0rc1"
        result = run_exact_dry(json.dumps(invalid))
        self.assertEqual(result.returncode, 4)
        self.assertIn("manifest tag does not match", result.stderr)

        invalid = manifest()
        invalid["plugin"]["version"] = "0.3.0-rc.1"
        result = run_exact_dry(json.dumps(invalid))
        self.assertEqual(result.returncode, 4)
        self.assertIn("plugin version does not match", result.stderr)

        result = run_exact_dry(
            json.dumps(manifest()).replace(
                '"schema_version": "benchwork-release-manifest/1.0"',
                '"schema_version": "benchwork-release-manifest/1.0", '
                '"schema_version": "duplicate"',
                1,
            )
        )
        self.assertEqual(result.returncode, 4)
        self.assertIn("duplicate", result.stderr)

    def test_rc_channel_verifies_its_manifest_descriptor(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = root / "home"
            fake_bin = root / "bin"
            artifacts = root / "artifacts"
            for path in (home, fake_bin, artifacts):
                path.mkdir()
            manifest_blob = json.dumps(manifest()).encode()
            (artifacts / "release-manifest.json").write_bytes(manifest_blob)
            channel = {
                "schema_version": "benchwork-release-channel/1.0",
                "channel": "rc",
                "version": "0.3.0rc2",
                "manifest_url": "https://example.test/releases/0.3.0rc2/release-manifest.json",
                "manifest_sha256": hashlib.sha256(manifest_blob).hexdigest(),
                "manifest_size": len(manifest_blob),
            }
            (artifacts / "rc.json").write_text(json.dumps(channel), encoding="utf-8")
            fake_curl = fake_bin / "curl"
            fake_curl.write_text(
                """#!/usr/bin/python3
import os, pathlib, shutil, sys
args = sys.argv[1:]
output = args[args.index("--output") + 1]
name = "rc.json" if args[-1].endswith("/channels/rc.json") else "release-manifest.json"
shutil.copyfile(pathlib.Path(os.environ["FAKE_ARTIFACTS"]) / name, output)
""",
                encoding="utf-8",
            )
            fake_curl.chmod(0o755)
            result = subprocess.run(
                [
                    "sh",
                    str(ROOT / "install.sh"),
                    "--channel",
                    "rc",
                    "--dry-run",
                    "--json",
                ],
                cwd=root,
                env={
                    **os.environ,
                    "HOME": str(home),
                    "PATH": f"{fake_bin}:/usr/bin:/bin",
                    "FAKE_ARTIFACTS": str(artifacts),
                    "BENCHWORK_INSTALLER_BASE_URL": "https://example.test",
                },
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            plan = json.loads(result.stdout)
            self.assertEqual(plan["version"], "0.3.0rc2")
            self.assertEqual(plan["channel"], "rc")

    def test_full_uv_lifecycle_is_idempotent_and_preserves_research_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = root / "home"
            work = root / "work"
            fake_bin = root / "fake-bin"
            tool_bin = root / "tool-bin"
            tool_dir = root / "tool-dir"
            artifacts = root / "artifacts"
            temporary = root / "tmp"
            runtime = root / "runtime"
            for path in (
                home,
                work,
                fake_bin,
                tool_bin,
                tool_dir,
                artifacts,
                temporary,
                runtime,
            ):
                path.mkdir()
            research = work / ".benchwork"
            research.mkdir()
            sentinel = research / "existing.txt"
            sentinel.write_text("preserve me\n", encoding="utf-8")

            wheel = artifacts / "benchwork.whl"
            wheel.write_bytes(b"fake exact wheel")
            plugin = artifacts / "plugin.tar.gz"
            subprocess.run(
                [
                    "python3",
                    str(ROOT / "scripts" / "installer" / "build-plugin-archive.py"),
                    str(plugin),
                ],
                check=True,
            )
            release = manifest()
            for descriptor, path in (
                (release["package"]["wheel"], wheel),
                (release["plugin"]["archive"], plugin),
            ):
                descriptor["size"] = path.stat().st_size
                descriptor["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
            manifest_path = artifacts / "release-manifest.json"
            manifest_path.write_text(json.dumps(release), encoding="utf-8")

            fake_curl = fake_bin / "curl"
            fake_curl.write_text(
                """#!/usr/bin/python3
import os, pathlib, shutil, sys
args = sys.argv[1:]
output = pathlib.Path(args[args.index("--output") + 1])
url = args[-1]
name = "release-manifest.json" if url.endswith("release-manifest.json") else pathlib.Path(url).name
mapping = {"benchwork.whl": "benchwork.whl", "plugin.tar.gz": "plugin.tar.gz"}
source = pathlib.Path(os.environ["FAKE_ARTIFACTS"]) / mapping.get(name, name)
shutil.copyfile(source, output)
""",
                encoding="utf-8",
            )
            fake_curl.chmod(0o755)

            fake_uv = fake_bin / "uv"
            fake_uv.write_text(
                f"""#!{shlex.quote(os.sys.executable)}
import os, pathlib, sys
args = sys.argv[1:]
log = pathlib.Path(os.environ["FAKE_UV_LOG"])
if args[:2] == ["tool", "install"]:
    with log.open("a", encoding="utf-8") as stream:
        stream.write("install\\n")
    target = pathlib.Path(os.environ["UV_TOOL_BIN_DIR"]) / "bwork"
    target.write_text(
        "#!{os.sys.executable}\\n"
        "from benchwork.cli import main\\n"
        "raise SystemExit(main())\\n",
        encoding="utf-8",
    )
    target.chmod(0o755)
    raise SystemExit(0)
if args[:2] == ["tool", "uninstall"]:
    (pathlib.Path(os.environ["FAKE_TOOL_BIN"]) / "bwork").unlink(missing_ok=True)
    raise SystemExit(0)
raise SystemExit(2)
""",
                encoding="utf-8",
            )
            fake_uv.chmod(0o755)
            uv_log = root / "uv.log"
            state_path = root / "data" / "benchwork" / "install-state.json"
            environment = {
                **os.environ,
                "HOME": str(home),
                "TMPDIR": str(temporary),
                "XDG_DATA_HOME": str(root / "data"),
                "XDG_RUNTIME_DIR": str(runtime),
                "BENCHWORK_INSTALL_STATE": str(state_path),
                "BENCHWORK_INSTALLER_BASE_URL": "https://example.test",
                "FAKE_ARTIFACTS": str(artifacts),
                "FAKE_TOOL_BIN": str(tool_bin),
                "FAKE_UV_LOG": str(uv_log),
                "PATH": f"{fake_bin}:/usr/bin:/bin",
            }
            command = [
                "sh",
                str(ROOT / "install.sh"),
                "--version",
                "0.3.0rc2",
                "--backend",
                "uv",
                "--install-dir",
                str(tool_dir),
                "--bin-dir",
                str(tool_bin),
                "--plugin-scope",
                "user",
                "--yes",
                "--json",
            ]
            first = subprocess.run(
                command,
                cwd=work,
                env=environment,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertTrue(json.loads(first.stdout)["ok"])
            first_state = state_path.read_bytes()
            self.assertEqual(sentinel.read_text(), "preserve me\n")
            self.assertTrue((root / "data" / "benchwork" / "plugins" / "current").is_symlink())

            second = subprocess.run(
                command,
                cwd=work,
                env=environment,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertTrue(json.loads(second.stdout)["already_healthy"])
            self.assertEqual(state_path.read_bytes(), first_state)
            self.assertEqual(uv_log.read_text().splitlines(), ["install"])

            removed = subprocess.run(
                ["sh", str(ROOT / "install.sh"), "--uninstall", "--json"],
                cwd=work,
                env={**environment, "PATH": f"{tool_bin}:{fake_bin}:/usr/bin:/bin"},
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(removed.returncode, 0, removed.stderr)
            self.assertEqual(json.loads(removed.stdout)["status"], "PASS")
            self.assertFalse(state_path.exists())
            self.assertFalse((tool_bin / "bwork").exists())
            self.assertEqual(sentinel.read_text(), "preserve me\n")
            self.assertEqual(list(temporary.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
