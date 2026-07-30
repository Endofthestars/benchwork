import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[2]
PLUGIN = ROOT / "plugins" / "benchwork"


class PluginPackageTest(unittest.TestCase):
    def test_manifest_marketplace_and_components_agree(self) -> None:
        manifest = json.loads(
            (PLUGIN / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        marketplace = json.loads(
            (ROOT / ".agents" / "plugins" / "marketplace.json").read_text(
                encoding="utf-8"
            )
        )
        entry = next(item for item in marketplace["plugins"] if item["name"] == "benchwork")
        self.assertEqual(marketplace["name"], "benchwork-local")
        self.assertEqual(manifest["name"], "benchwork")
        self.assertEqual(manifest["version"], "0.3.0-alpha.1")
        self.assertEqual(entry["source"]["path"], "./plugins/benchwork")
        self.assertEqual(entry["policy"]["installation"], "AVAILABLE")
        self.assertEqual(entry["policy"]["authentication"], "ON_INSTALL")
        self.assertNotIn("hooks", manifest)
        self.assertTrue((PLUGIN / "hooks" / "hooks.json").is_file())
        self.assertEqual(
            len(list((PLUGIN / "skills").glob("*/SKILL.md"))),
            7,
        )

    def test_packaging_files_do_not_reference_canonical_project_state(self) -> None:
        files = [
            PLUGIN / ".codex-plugin" / "plugin.json",
            PLUGIN / ".mcp.json",
            ROOT / ".agents" / "plugins" / "marketplace.json",
        ]
        before = {
            path: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in files
        }
        for path in files:
            json.loads(path.read_text(encoding="utf-8"))
        after = {
            path: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in files
        }
        self.assertEqual(before, after)
