import json
import tomllib
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[2]
PLUGIN = ROOT / "plugins" / "benchwork"


class CodexInteractiveContractTest(unittest.TestCase):
    def test_project_config_and_plugin_use_the_same_stdio_server(self) -> None:
        config = tomllib.loads(
            (ROOT / ".codex" / "config.toml.example").read_text(encoding="utf-8")
        )
        plugin_mcp = json.loads(
            (PLUGIN / ".mcp.json").read_text(encoding="utf-8")
        )["mcpServers"]["benchwork"]
        project_mcp = config["mcp_servers"]["benchwork"]
        self.assertEqual(project_mcp["command"], plugin_mcp["command"])
        self.assertEqual(project_mcp["args"], plugin_mcp["args"])
        self.assertEqual([project_mcp["command"], *project_mcp["args"]], [
            "bwork",
            "mcp",
            "serve",
        ])

    def test_orchestrator_supports_explicit_and_broad_request_selection(self) -> None:
        skill = (
            PLUGIN / "skills" / "benchwork-orchestrate" / "SKILL.md"
        ).read_text(encoding="utf-8")
        metadata = (
            PLUGIN / "skills" / "benchwork-orchestrate" / "agents" / "openai.yaml"
        ).read_text(encoding="utf-8")
        self.assertIn("$benchwork-orchestrate", metadata)
        self.assertIn("start a research project", skill.lower())
        self.assertIn("what should we do next", skill.lower())

    def test_implementation_skill_keeps_external_review_approval_separate(self) -> None:
        skill = (
            PLUGIN / "skills" / "benchwork-implement" / "SKILL.md"
        ).read_text(encoding="utf-8")
        policy = (
            PLUGIN
            / "skills"
            / "benchwork-implement"
            / "references"
            / "review-policy.md"
        ).read_text(encoding="utf-8")
        self.assertIn("external reviewer", skill)
        self.assertIn("benchwork_prepare_review", policy)
        self.assertIn("benchwork_approve_external_review", policy)
        self.assertIn("same `review_id`", policy)

    def test_review_policy_distinguishes_host_trust_from_on_device_execution(self) -> None:
        policy = (ROOT / "docs" / "en" / "REVIEW_DISCLOSURE_POLICY.md").read_text(
            encoding="utf-8"
        )
        normalized = " ".join(policy.split())
        self.assertIn(
            "does not claim that a hosted Agent model runs on-device",
            normalized,
        )
        self.assertIn(
            "no additional provider, destination, export, or disclosure",
            normalized,
        )
        self.assertIn("WAITING_FOR_DISCLOSURE_AUTHORIZATION", normalized)
        self.assertIn("A Review Artifact cannot", normalized)
