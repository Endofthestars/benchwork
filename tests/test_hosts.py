import tempfile
import unittest
from pathlib import Path

from benchwork.athanor import Athanor
from benchwork.circle import CapsuleStore, CapabilityRegistry
from benchwork.hosts import ClaudeCodeHostAdapter, CodexHostAdapter


class HostAdapterTest(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        root = Path(self.directory.name)
        self.athanor = Athanor(root)
        self.registry = CapabilityRegistry(root)
        self.capsules = CapsuleStore(root)
        self.program_id, _ = self.athanor.create_program(
            "host-symmetry",
            "Host symmetry",
        )

    def tearDown(self) -> None:
        self.directory.cleanup()

    def test_hosts_produce_equivalent_non_gated_proposals(self) -> None:
        codex = CodexHostAdapter(self.athanor, self.registry, self.capsules).propose(
            "bench.code.inspect",
            self.program_id,
            "Inspect the registered code.",
            ["read"],
            300,
            False,
        )
        claude = ClaudeCodeHostAdapter(self.athanor, self.registry, self.capsules).propose(
            "bench.code.inspect",
            self.program_id,
            "Inspect the registered code.",
            ["read"],
            300,
            False,
        )
        self.assertEqual(codex.ward.status, "PASS")
        self.assertEqual(claude.ward.status, "PASS")
        self.assertEqual(codex.capsule["host"], "codex")
        self.assertEqual(claude.capsule["host"], "claude-code")
        self.assertEqual(codex.capsule["expected_outputs"], claude.capsule["expected_outputs"])
        self.assertEqual(
            codex.capsule["capability"],
            claude.capsule["capability"],
        )
        self.assertEqual(codex.as_dict()["next_action"], "delegate_to_host")

    def test_hosts_share_the_same_approval_gate(self) -> None:
        proposal = ClaudeCodeHostAdapter(self.athanor, self.registry, self.capsules).propose(
            "bench.code.modify",
            self.program_id,
            "Modify the registered code.",
            ["read", "write"],
            300,
            False,
        )
        self.assertEqual(proposal.ward.status, "WAITING_FOR_APPROVAL")
        self.assertEqual(proposal.as_dict()["next_action"], "await_human_approval")
