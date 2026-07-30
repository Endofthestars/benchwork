import json
import re
import unittest
from pathlib import Path

from benchwork.mcp.tool_registry import tool_names
from benchwork.schema_validation import validate_instance


ROOT = Path(__file__).parents[2]
PLUGIN = ROOT / "plugins" / "benchwork"
FRONTMATTER_NAME = re.compile(r"^---\nname: ([a-z0-9-]+)\n", re.MULTILINE)


class PluginReleaseMetadataTest(unittest.TestCase):
    def test_plugin_companion_manifest_matches_native_manifest_and_registry(self) -> None:
        native = json.loads(
            (PLUGIN / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        companion = json.loads(
            (PLUGIN / "benchwork-plugin-api.json").read_text(encoding="utf-8")
        )
        validate_instance("benchwork-plugin-api-1.0.json", companion)
        self.assertEqual(companion["plugin"], native["name"])
        self.assertEqual(companion["plugin_version"], native["version"])
        self.assertEqual(companion["mcp_tool_count"], len(tool_names()))
        self.assertNotIn("benchwork_api", native)
        self.assertNotIn("minimum_runtime", native)
        self.assertNotIn("skills_api", native)

    def test_every_skill_has_valid_versioned_metadata_and_native_dependency(self) -> None:
        registered = set(tool_names())
        skill_directories = sorted(
            path.parent for path in (PLUGIN / "skills").glob("*/SKILL.md")
        )
        self.assertEqual(len(skill_directories), 7)
        for directory in skill_directories:
            with self.subTest(skill=directory.name):
                metadata = json.loads(
                    (directory / "skill.yaml").read_text(encoding="utf-8")
                )
                validate_instance("benchwork-skill-metadata-1.0.json", metadata)
                skill_text = (directory / "SKILL.md").read_text(encoding="utf-8")
                match = FRONTMATTER_NAME.search(skill_text)
                self.assertIsNotNone(match)
                assert match is not None
                self.assertEqual(metadata["name"], directory.name)
                self.assertEqual(metadata["name"], match.group(1))
                self.assertTrue(set(metadata["requires"]["mcp"]) <= registered)
                host_metadata = (directory / "agents" / "openai.yaml").read_text(
                    encoding="utf-8"
                )
                self.assertIn('type: "mcp"', host_metadata)
                self.assertIn('value: "benchwork"', host_metadata)

    def test_skill_metadata_does_not_replace_native_discovery(self) -> None:
        manifest = json.loads(
            (PLUGIN / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["skills"], "./skills/")
        for directory in (PLUGIN / "skills").iterdir():
            if directory.is_dir():
                self.assertTrue((directory / "SKILL.md").is_file())
                self.assertTrue((directory / "agents" / "openai.yaml").is_file())
