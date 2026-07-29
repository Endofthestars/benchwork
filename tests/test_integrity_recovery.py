import tempfile
import unittest
from pathlib import Path

from benchwork.athanor import Athanor, AthanorError


class IntegrityRecoveryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.athanor = Athanor(self.root)

    def tearDown(self) -> None:
        self.directory.cleanup()

    def _program_with_protocol(self, slug: str = "recovery-study") -> tuple[str, str]:
        program_id, _ = self.athanor.create_program(slug, "Recovery study")
        protocol_id = f"PT-{len(self.athanor.protocols()) + 1:03d}"
        self.athanor.draft_protocol(
            protocol_id,
            program_id,
            "Recovery protocol",
            "Compute the registered metrics without changing the sealed design.",
        )
        self.athanor.seal_protocol(protocol_id)
        return program_id, protocol_id

    def test_artifact_issue_and_deviation_are_replayable(self) -> None:
        program_id, protocol_id = self._program_with_protocol()
        artifact_receipt = self.athanor.register_artifact(
            "AR-001",
            program_id,
            "implementation",
            {
                "uri": "artifacts/implementation.json",
                "sigil": "sha256:" + "a" * 64,
            },
            protocol_id,
            [program_id],
        )
        issue_receipt = self.athanor.open_issue(
            "IS-001",
            program_id,
            ["AR-001"],
            "HIGH",
            "Incomplete environment record",
            "The implementation Artifact omits one environment field.",
        )
        deviation_receipt = self.athanor.record_deviation(
            "DV-001",
            protocol_id,
            "UNPLANNED",
            "Environment metadata repaired after the pilot.",
            "The missing field prevented exact replay.",
            "MINOR",
            ["AR-001", "IS-001"],
        )
        resolution_receipt = self.athanor.resolve_issue(
            "IS-001",
            "Registered the missing field and preserved the original Artifact.",
        )

        state = self.athanor.replay()
        program = state["programs"][program_id]
        self.assertEqual(program["artifacts"], ["AR-001"])
        self.assertEqual(program["issues"], ["IS-001"])
        self.assertEqual(program["deviations"], ["DV-001"])
        self.assertEqual(state["protocols"][protocol_id]["deviations"], ["DV-001"])

        artifact = state["artifacts"]["AR-001"]
        self.assertEqual(artifact["registration_receipt"], artifact_receipt.receipt_id)
        self.assertEqual(artifact["producer_id"], protocol_id)
        issue = state["issues"]["IS-001"]
        self.assertEqual(issue["status"], "RESOLVED")
        self.assertEqual(issue["open_receipt"], issue_receipt.receipt_id)
        self.assertEqual(issue["resolution_receipt"], resolution_receipt.receipt_id)
        deviation = state["deviations"]["DV-001"]
        self.assertEqual(deviation["record_receipt"], deviation_receipt.receipt_id)
        self.assertEqual(deviation["impact"], "MINOR")

        self.assertEqual(
            [event["type"] for event in self.athanor.trace("AR-001")],
            ["artifact.registered", "issue.opened", "deviation.recorded"],
        )

    def test_cross_program_references_fail_before_append(self) -> None:
        first, first_protocol = self._program_with_protocol("first-recovery")
        second, second_protocol = self._program_with_protocol("second-recovery")
        event_count = len(self.athanor.chronicle.events())

        with self.assertRaisesRegex(AthanorError, "does not belong"):
            self.athanor.register_artifact(
                "AR-001",
                second,
                "implementation",
                {"uri": "artifact.json", "sigil": "sha256:" + "b" * 64},
                first_protocol,
            )
        self.assertEqual(len(self.athanor.chronicle.events()), event_count)

        with self.assertRaisesRegex(AthanorError, "does not belong"):
            self.athanor.open_issue(
                "IS-001",
                second,
                [first_protocol],
                "MEDIUM",
                "Cross-program subject",
                "This reference must be rejected.",
            )
        self.assertEqual(len(self.athanor.chronicle.events()), event_count)

        with self.assertRaisesRegex(AthanorError, "must belong"):
            self.athanor.record_deviation(
                "DV-001",
                second_protocol,
                "PLANNED",
                "Cross-program affected object.",
                "Exercise the reference boundary.",
                "NONE",
                [first],
            )
        self.assertEqual(len(self.athanor.chronicle.events()), event_count)

    def test_deviation_requires_a_frozen_protocol_and_preserves_it(self) -> None:
        program_id, _ = self.athanor.create_program("frozen-design", "Frozen design")
        self.athanor.draft_protocol(
            "PT-001",
            program_id,
            "Original title",
            "Original analysis plan.",
        )
        event_count = len(self.athanor.chronicle.events())
        with self.assertRaisesRegex(AthanorError, "frozen Protocol"):
            self.athanor.record_deviation(
                "DV-001",
                "PT-001",
                "PLANNED",
                "Premature deviation.",
                "There is no sealed commitment yet.",
                "NONE",
            )
        self.assertEqual(len(self.athanor.chronicle.events()), event_count)

        self.athanor.seal_protocol("PT-001")
        self.athanor.record_deviation(
            "DV-001",
            "PT-001",
            "PLANNED",
            "Add a robustness analysis.",
            "The primary analysis remains unchanged.",
            "MINOR",
        )
        protocol = self.athanor.protocols()["PT-001"]
        self.assertEqual(protocol["title"], "Original title")
        self.assertEqual(protocol["analysis_plan"], "Original analysis plan.")
        self.assertEqual(protocol["status"], "FROZEN")

    def test_resolved_issue_cannot_be_resolved_again(self) -> None:
        program_id, _ = self._program_with_protocol()
        self.athanor.open_issue(
            "IS-001",
            program_id,
            [program_id],
            "LOW",
            "Document a limitation",
            "The limitation must remain in Chronicle.",
        )
        self.athanor.resolve_issue("IS-001", "The limitation is now documented.")
        event_count = len(self.athanor.chronicle.events())
        with self.assertRaisesRegex(AthanorError, "not open"):
            self.athanor.resolve_issue("IS-001", "A second resolution is invalid.")
        self.assertEqual(len(self.athanor.chronicle.events()), event_count)

    def test_optional_reference_lists_reject_other_container_types(self) -> None:
        program_id, protocol_id = self._program_with_protocol()
        with self.assertRaisesRegex(AthanorError, "input IDs"):
            self.athanor.register_artifact(
                "AR-001",
                program_id,
                "implementation",
                {"uri": "artifact.json", "sigil": "sha256:" + "c" * 64},
                protocol_id,
                (),
            )
        with self.assertRaisesRegex(AthanorError, "affected object IDs"):
            self.athanor.record_deviation(
                "DV-001",
                protocol_id,
                "PLANNED",
                "Invalid container type.",
                "Only JSON-compatible lists are accepted.",
                "NONE",
                (),
            )
