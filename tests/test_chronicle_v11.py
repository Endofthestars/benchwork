import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from benchwork.athanor import Athanor, AthanorError, canonical_json, content_sigil


class ChronicleV11Test(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.athanor = Athanor(self.root)

    def tearDown(self) -> None:
        self.directory.cleanup()

    @property
    def ledger(self) -> Path:
        return self.root / ".benchwork" / "chronicle.jsonl"

    @property
    def head(self) -> Path:
        return self.root / ".benchwork" / "chronicle.head"

    def _create_program(self, slug: str = "integrity") -> None:
        self.athanor.create_program(slug, slug.title())

    def _mutate_first_event(self, mutate) -> None:
        event = json.loads(self.ledger.read_text(encoding="utf-8").splitlines()[0])
        mutate(event)
        self.ledger.write_text(canonical_json(event) + "\n", encoding="utf-8")

    def _write_v10_program(self) -> list[dict]:
        occurred_at = "2026-07-29T00:00:00+00:00"
        event_body = {
            "schema_version": "chronicle-event/1.0",
            "event_id": "CE-LEGACY001",
            "type": "program.created",
            "object_id": "RP-001",
            "occurred_at": occurred_at,
            "previous_sigil": None,
            "payload": {
                "slug": "legacy-study",
                "title": "Legacy study",
                "problem": {"statement": "Preserve this projection."},
            },
        }
        sigil = content_sigil(event_body)
        event = {
            **event_body,
            "receipt": {
                "receipt_id": "RC-LEGACY001",
                "event_id": "CE-LEGACY001",
                "sigil": sigil,
                "previous_sigil": None,
                "accepted_at": occurred_at,
            },
        }
        base = self.root / ".benchwork"
        base.mkdir()
        self.ledger.write_text(canonical_json(event) + "\n", encoding="utf-8")
        self.head.write_text(
            canonical_json({"count": 1, "sigil": sigil}) + "\n",
            encoding="utf-8",
        )
        return [event]

    def test_receipt_identity_and_acceptance_time_are_bound(self) -> None:
        for field, value in (
            ("receipt_id", "RC-TAMPERED"),
            ("accepted_at", "2026-07-29T00:00:01+00:00"),
        ):
            with self.subTest(field=field):
                self._create_program(field.replace("_", "-"))
                self._mutate_first_event(
                    lambda event, field=field, value=value: event["receipt"].__setitem__(
                        field, value
                    )
                )
                with self.assertRaisesRegex(AthanorError, "Receipt Sigil|acceptance time"):
                    self.athanor.chronicle.events()
                self.directory.cleanup()
                self.directory = tempfile.TemporaryDirectory()
                self.root = Path(self.directory.name)
                self.athanor = Athanor(self.root)

    def test_unknown_event_and_receipt_properties_fail_verification(self) -> None:
        for target in ("event", "receipt"):
            with self.subTest(target=target):
                self._create_program(f"unknown-{target}")
                if target == "event":
                    self._mutate_first_event(
                        lambda event: event.__setitem__("unexpected", True)
                    )
                else:
                    self._mutate_first_event(
                        lambda event: event["receipt"].__setitem__("unexpected", True)
                    )
                with self.assertRaisesRegex(AthanorError, "validation failed"):
                    self.athanor.chronicle.events()
                self.directory.cleanup()
                self.directory = tempfile.TemporaryDirectory()
                self.root = Path(self.directory.name)
                self.athanor = Athanor(self.root)

    def test_valid_tail_recovery_updates_only_the_head(self) -> None:
        self._create_program("first")
        old_head = self.head.read_bytes()
        self._create_program("second")
        ledger_before_recovery = self.ledger.read_bytes()
        self.head.write_bytes(old_head)

        with self.assertRaisesRegex(AthanorError, "head mismatch"):
            self.athanor.chronicle.events()
        dry_run = self.athanor.recover_chronicle()
        self.assertEqual(dry_run["status"], "RECOVERABLE")
        self.assertEqual(dry_run["tail_event_count"], 1)
        self.assertFalse(dry_run["head_updated"])
        self.assertEqual(self.head.read_bytes(), old_head)

        accepted = self.athanor.recover_chronicle(accept_valid_tail=True)
        self.assertEqual(accepted["status"], "RECOVERED")
        self.assertTrue(accepted["head_updated"])
        self.assertEqual(self.ledger.read_bytes(), ledger_before_recovery)
        self.assertEqual(len(self.athanor.chronicle.events()), 2)

    def test_invalid_tail_cannot_be_recovered(self) -> None:
        self._create_program("first")
        old_head = self.head.read_bytes()
        self._create_program("second")
        events = [
            json.loads(line)
            for line in self.ledger.read_text(encoding="utf-8").splitlines()
        ]
        events[-1]["receipt"]["receipt_id"] = "RC-TAMPERED"
        self.ledger.write_text(
            "".join(canonical_json(event) + "\n" for event in events),
            encoding="utf-8",
        )
        self.head.write_bytes(old_head)

        with self.assertRaisesRegex(AthanorError, "Receipt Sigil"):
            self.athanor.recover_chronicle(accept_valid_tail=True)
        self.assertEqual(self.head.read_bytes(), old_head)

    def test_commit_failure_leaves_a_recoverable_valid_tail(self) -> None:
        self._create_program("first")
        with patch.object(
            self.athanor.chronicle,
            "_write_head",
            side_effect=OSError("injected head commit failure"),
        ):
            with self.assertRaisesRegex(OSError, "injected"):
                self._create_program("second")

        report = self.athanor.recover_chronicle(accept_valid_tail=True)
        self.assertEqual(report["tail_event_count"], 1)
        self.assertEqual(len(self.athanor.programs()), 2)

    def test_v10_migration_preserves_projection_and_creates_backup(self) -> None:
        old_events = self._write_v10_program()
        expected_projection = self.athanor._project(old_events)

        with self.assertRaisesRegex(AthanorError, "explicit migration"):
            self.athanor.chronicle.events()
        report = self.athanor.migrate_chronicle_v10_to_v11()

        self.assertTrue(report["projection_preserved"])
        self.assertEqual(report["event_count"], 1)
        self.assertEqual(self.athanor.replay(), expected_projection)
        migrated_event = self.athanor.chronicle.events()[0]
        self.assertEqual(migrated_event["schema_version"], "chronicle-event/1.1")
        self.assertEqual(migrated_event["payload"], old_events[0]["payload"])
        backup = self.root / ".benchwork" / report["backup_directory"]
        self.assertTrue((backup / "chronicle.jsonl.v1.0").is_file())
        self.assertTrue((backup / "chronicle.head.v1.0").is_file())
        self.assertTrue((backup / "migration-report.json").is_file())

        with self.assertRaisesRegex(AthanorError, "already v1.1"):
            self.athanor.migrate_chronicle_v10_to_v11()

    def test_v10_migration_resumes_from_every_commit_point(self) -> None:
        for fault_point in (
            "after_backup",
            "after_ledger_replace",
            "before_head_replace",
            "after_head_replace_before_report",
        ):
            with self.subTest(fault_point=fault_point):
                old_events = self._write_v10_program()
                expected_projection = self.athanor._project(old_events)

                def inject(point: str) -> None:
                    if point == fault_point:
                        raise OSError(f"injected migration failure at {point}")

                with patch.object(
                    self.athanor.chronicle,
                    "_migration_fault",
                    side_effect=inject,
                ):
                    with self.assertRaisesRegex(OSError, fault_point):
                        self.athanor.migrate_chronicle_v10_to_v11()

                pending = self.root / ".benchwork" / "migration.pending"
                self.assertTrue(pending.is_file())
                report = self.athanor.migrate_chronicle_v10_to_v11()
                self.assertTrue(report["projection_preserved"])
                self.assertEqual(self.athanor.replay(), expected_projection)
                self.assertFalse(pending.exists())
                backup = self.root / ".benchwork" / report["backup_directory"]
                self.assertTrue((backup / "migration-report.json").is_file())

                self.directory.cleanup()
                self.directory = tempfile.TemporaryDirectory()
                self.root = Path(self.directory.name)
                self.athanor = Athanor(self.root)

    def test_malformed_v10_input_fails_closed_without_backup(self) -> None:
        self._write_v10_program()
        event = json.loads(self.ledger.read_text(encoding="utf-8"))
        event["payload"]["title"] = "Tampered"
        self.ledger.write_text(canonical_json(event) + "\n", encoding="utf-8")

        with self.assertRaisesRegex(AthanorError, "invalid v1.0 Sigil"):
            self.athanor.migrate_chronicle_v10_to_v11()
        self.assertFalse((self.root / ".benchwork" / "migrations").exists())

    def test_v10_unknown_fields_are_not_silently_dropped(self) -> None:
        self._write_v10_program()
        event = json.loads(self.ledger.read_text(encoding="utf-8"))
        event["legacy_extension"] = {"must": "not disappear"}
        event_body = {key: value for key, value in event.items() if key != "receipt"}
        event["receipt"]["sigil"] = content_sigil(event_body)
        self.ledger.write_text(canonical_json(event) + "\n", encoding="utf-8")
        self.head.write_text(
            canonical_json({"count": 1, "sigil": event["receipt"]["sigil"]}) + "\n",
            encoding="utf-8",
        )

        with self.assertRaisesRegex(AthanorError, "unsupported v1.0 fields"):
            self.athanor.migrate_chronicle_v10_to_v11()
        self.assertFalse((self.root / ".benchwork" / "migrations").exists())
