import json
import multiprocessing as mp
import tempfile
import unittest
from pathlib import Path

from benchwork.athanor import Athanor, AthanorError, content_sigil
from benchwork.rites import RiteRegistry


def _concurrent_install(argument: tuple[str, str]) -> bool:
    root, source = argument
    return RiteRegistry(Path(root)).install_grimoire(Path(source))[2]


def _write_grimoire(
    source: Path,
    *,
    grimoire_id: str = "example/research-methods",
    version: str = "1.0.0",
    rite_id: str = "ablation-study@1.0.0",
    stages: list[dict[str, str]] | None = None,
    benchwork_api: str = "0.1",
) -> dict:
    definition = {
        "schema_version": "rite/1.0",
        "rite_id": rite_id,
        "description": "A compact extension Rite used by the test suite.",
        "stages": stages
        or [
            {"name": "PREPARE", "exit_artifact": "dataset-manifest"},
            {"name": "EXECUTE", "exit_artifact": "run-record"},
            {"name": "ASSESS", "exit_artifact": "assessment"},
        ],
    }
    rite_path = source / "rites" / "ablation.json"
    rite_path.parent.mkdir(parents=True)
    rite_path.write_text(json.dumps(definition), encoding="utf-8")
    manifest = {
        "schema_version": "grimoire-manifest/1.0",
        "grimoire_id": grimoire_id,
        "version": version,
        "benchwork_api": benchwork_api,
        "rites": [
            {
                "rite_id": rite_id,
                "path": "rites/ablation.json",
                "sigil": content_sigil(definition),
            }
        ],
    }
    (source / "grimoire.json").write_text(json.dumps(manifest), encoding="utf-8")
    return definition


class GrimoireTest(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name) / "project"
        self.source = Path(self.directory.name) / "source"
        self.root.mkdir()
        self.source.mkdir()
        self.registry = RiteRegistry(self.root)

    def tearDown(self) -> None:
        self.directory.cleanup()

    def test_install_pins_content_and_custom_rite_drives_a_working(self) -> None:
        definition = _write_grimoire(self.source)
        grimoire_ref, manifest_sigil, installed = self.registry.install_grimoire(self.source)
        self.assertEqual(grimoire_ref, "example/research-methods@1.0.0")
        self.assertTrue(manifest_sigil.startswith("sha256:"))
        self.assertTrue(installed)
        self.assertEqual(self.registry.install_grimoire(self.source)[2], False)

        definition["description"] = "The source changed after installation."
        (self.source / "rites" / "ablation.json").write_text(json.dumps(definition), encoding="utf-8")
        pinned = self.registry.get("ablation-study@1.0.0")
        self.assertNotEqual(pinned["description"], definition["description"])
        manifest_path = self.source / "grimoire.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["rites"][0]["sigil"] = content_sigil(definition)
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaisesRegex(AthanorError, "version has different content"):
            self.registry.install_grimoire(self.source)

        athanor = Athanor(self.root)
        program_id, _ = athanor.create_program("extension-study", "Extension study")
        athanor.draft_protocol("PT-001", program_id, "Extension", "Use the pinned analysis plan.")
        athanor.seal_protocol("PT-001")
        working_id, _ = athanor.create_working("ablation-study@1.0.0", program_id, "PT-001")
        working = athanor.workings()[working_id]
        self.assertEqual(working["stage"], "PREPARE")
        self.assertEqual(working["rite_sigil"], content_sigil(pinned))

        with self.assertRaisesRegex(AthanorError, "manual Working advancement is deprecated"):
            athanor.advance_working(working_id, "Dataset fixed.", [])
        self.assertEqual(athanor.workings()[working_id]["stage"], "PREPARE")

    def test_install_rejects_rite_content_drift(self) -> None:
        definition = _write_grimoire(self.source)
        definition["description"] = "Changed without updating the manifest."
        (self.source / "rites" / "ablation.json").write_text(json.dumps(definition), encoding="utf-8")
        with self.assertRaisesRegex(AthanorError, "Sigil mismatch"):
            self.registry.install_grimoire(self.source)

    def test_install_rejects_path_traversal(self) -> None:
        _write_grimoire(self.source)
        manifest_path = self.source / "grimoire.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["rites"][0]["path"] = "../outside.json"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaisesRegex(AthanorError, "unsafe or duplicate"):
            self.registry.install_grimoire(self.source)

    def test_install_rejects_symlink_escape(self) -> None:
        definition = _write_grimoire(self.source)
        outside = Path(self.directory.name) / "outside.json"
        outside.write_text(json.dumps(definition), encoding="utf-8")
        linked = self.source / "rites" / "linked.json"
        linked.symlink_to(outside)
        manifest_path = self.source / "grimoire.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["rites"][0]["path"] = "rites/linked.json"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaisesRegex(AthanorError, "escapes its source"):
            self.registry.install_grimoire(self.source)

    def test_install_rejects_reserved_and_cross_grimoire_collisions(self) -> None:
        reserved_source = Path(self.directory.name) / "reserved"
        reserved_source.mkdir()
        _write_grimoire(reserved_source, rite_id="computational-study@0.1.0")
        with self.assertRaisesRegex(AthanorError, "reserved Rite"):
            self.registry.install_grimoire(reserved_source)

        _write_grimoire(self.source)
        self.registry.install_grimoire(self.source)
        second = Path(self.directory.name) / "second"
        second.mkdir()
        _write_grimoire(second, grimoire_id="example/other-methods")
        with self.assertRaisesRegex(AthanorError, "another Grimoire"):
            self.registry.install_grimoire(second)

    def test_install_rejects_duplicate_stages_and_unsupported_api(self) -> None:
        _write_grimoire(
            self.source,
            stages=[
                {"name": "RUN", "exit_artifact": "run-record"},
                {"name": "RUN", "exit_artifact": "result-bundle"},
            ],
        )
        with self.assertRaisesRegex(AthanorError, "duplicate stage names"):
            self.registry.install_grimoire(self.source)

        incompatible = Path(self.directory.name) / "incompatible"
        incompatible.mkdir()
        _write_grimoire(incompatible, benchwork_api="9.0")
        with self.assertRaisesRegex(AthanorError, "supported API is 0.1"):
            self.registry.install_grimoire(incompatible)

    def test_install_rejects_duplicate_json_keys(self) -> None:
        _write_grimoire(self.source)
        manifest_path = self.source / "grimoire.json"
        raw = manifest_path.read_text(encoding="utf-8")
        raw = raw.replace('"version": "1.0.0",', '"version": "1.0.0", "version": "2.0.0",')
        manifest_path.write_text(raw, encoding="utf-8")
        with self.assertRaisesRegex(AthanorError, "duplicate JSON key"):
            self.registry.install_grimoire(self.source)

    def test_repository_example_is_installable(self) -> None:
        example = Path(__file__).parents[1] / "examples" / "open-grimoire"
        grimoire_ref, _, installed = self.registry.install_grimoire(example)
        self.assertEqual(grimoire_ref, "endofthestars/example-methods@0.1.0")
        self.assertTrue(installed)
        self.assertIn("ablation-study@0.1.0", self.registry.rites())

    def test_legacy_builtin_registry_is_normalized(self) -> None:
        state = self.root / ".benchwork"
        state.mkdir()
        legacy = {
            "schema_version": "rite-registry/1.0",
            "rites": {
                "legacy-study@1.0.0": {
                    "description": "A pre-Grimoire Rite definition.",
                    "stages": [{"name": "RUN", "exit_artifact": "run-record"}],
                }
            },
        }
        (state / "rites.json").write_text(json.dumps(legacy), encoding="utf-8")
        definition = self.registry.get("legacy-study@1.0.0")
        self.assertEqual(definition["schema_version"], "rite/1.0")
        self.assertEqual(definition["rite_id"], "legacy-study@1.0.0")

    def test_concurrent_install_is_idempotent(self) -> None:
        _write_grimoire(self.source)
        context = mp.get_context("fork")
        with context.Pool(2) as pool:
            installed = pool.map(
                _concurrent_install,
                [(str(self.root), str(self.source)), (str(self.root), str(self.source))],
            )
        self.assertEqual(sorted(installed), [False, True])
        self.assertEqual(len(self.registry.grimoires()), 1)

    def test_registry_tampering_fails_closed(self) -> None:
        _write_grimoire(self.source)
        self.registry.install_grimoire(self.source)
        path = self.root / ".benchwork" / "grimoires.json"
        registry = json.loads(path.read_text(encoding="utf-8"))
        registry["grimoires"]["example/research-methods@1.0.0"]["manifest_sigil"] = "sha256:" + "0" * 64
        path.write_text(json.dumps(registry), encoding="utf-8")
        with self.assertRaisesRegex(AthanorError, "invalid installed Grimoire identity"):
            self.registry.grimoires()
