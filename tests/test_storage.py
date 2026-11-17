"""Tests for SQLite storage persistence and isolation."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import storage


class StorageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test.sqlite3"
        self.path_patch = patch.object(storage, "DB_PATH", self.db_path)
        self.path_patch.start()
        storage.init_storage()

    def tearDown(self) -> None:
        self.path_patch.stop()
        self.temp_dir.cleanup()

    def test_warning_counts_persist_and_are_scoped(self) -> None:
        self.assertEqual(storage.add_warning(-100, 7), 1)
        self.assertEqual(storage.add_warning(-100, 7), 2)
        self.assertEqual(storage.get_warnings(-100, 7), 2)
        self.assertEqual(storage.get_warnings(-200, 7), 0)
        storage.reset_warnings(-100, 7)
        self.assertEqual(storage.get_warnings(-100, 7), 0)

    def test_feature_settings_and_allowlists_persist(self) -> None:
        storage.set_feature_enabled("antilink", -100, False)
        self.assertFalse(storage.is_feature_enabled("antilink", -100))
        self.assertTrue(storage.is_feature_enabled("badwords", -100))
        storage.add_allowed_domain(-100, "example.com")
        self.assertEqual(storage.get_allowed_domains(-100), {"example.com"})
        storage.remove_allowed_domain(-100, "example.com")
        self.assertEqual(storage.get_allowed_domains(-100), set())

    def test_badwords_persist_and_are_scoped(self) -> None:
        storage.add_badword(-100, "spoiler")
        storage.add_badword(-100, "spoiler")
        storage.add_badword(-200, "other")
        self.assertEqual(storage.get_badwords(-100), {"spoiler"})
        storage.remove_badword(-100, "spoiler")
        self.assertEqual(storage.get_badwords(-100), set())

    def test_verification_challenge_persists_and_expires(self) -> None:
        permissions = {"can_send_messages": False}
        storage.save_verification(-100, 7, 2, 500, permissions)
        self.assertEqual(
            storage.get_verification(-100, 7),
            {"correct_index": 2, "expires_at": 500, "permissions": permissions},
        )
        storage.cleanup_verifications(500)
        self.assertIsNone(storage.get_verification(-100, 7))

    def test_security_audit_is_bounded_and_readable(self) -> None:
        storage.record_audit_event(-100, "ban", 7, 8, "manual action")
        events = storage.get_audit_events(10)
        self.assertEqual(events[0]["action"], "ban")
        self.assertEqual(events[0]["actor_id"], 7)
        self.assertEqual(events[0]["target_id"], 8)
        self.assertEqual(events[0]["details"], "manual action")

    def test_copyright_protection_defaults_on_and_can_be_toggled(self) -> None:
        self.assertTrue(storage.is_copyright_enabled(-100))
        storage.set_copyright_enabled(-100, False)
        self.assertFalse(storage.is_copyright_enabled(-100))
        storage.set_copyright_enabled(-100, True)
        self.assertTrue(storage.is_copyright_enabled(-100))

    def test_database_backup_is_valid_sqlite(self) -> None:
        backup = storage.create_database_backup()
        self.assertTrue(backup.startswith(b"SQLite format 3"))
        status = storage.get_database_status()
        self.assertEqual(status["integrity"], "ok")
        self.assertTrue(status["exists"])
        self.assertGreaterEqual(status["table_count"], 10)

    def test_owner_security_intelligence_records_group_joins_and_incidents(self) -> None:
        storage.register_group(-100, "Ani World Main")
        storage.record_member_join(-100, "Ani World Main", 7, "sample_user", "Sample User")
        storage.record_security_incident(
            -100, "Ani World Main", "raid_detected", "critical",
            details="rapid join spike",
        )
        self.assertEqual(storage.get_known_groups()[0]["title"], "Ani World Main")
        self.assertEqual(storage.get_recent_member_joins()[0]["username"], "sample_user")
        self.assertEqual(storage.get_recent_security_incidents()[0]["kind"], "raid_detected")
        summary = storage.get_owner_security_summary()
        self.assertEqual(summary["groups"], 1)
        self.assertEqual(summary["joins_24h"], 1)
        self.assertEqual(summary["incidents_24h"], 1)
        self.assertEqual(summary["raids_7d"], 1)

    def test_raid_join_window_and_mode_persist(self) -> None:
        self.assertEqual(storage.record_raid_joins(-100, 3, 1000.0, 60), 3)
        self.assertEqual(storage.get_raid_join_count(-100, 1010.0, 60), 3)
        self.assertEqual(storage.get_raid_join_count(-100, 1100.0, 60), 0)
        storage.set_raid_expiry(-100, 1200.0)
        self.assertEqual(storage.get_raid_expiry(-100), 1200.0)
        self.assertTrue(storage.clear_raid_expiry(-100))
        self.assertFalse(storage.clear_raid_expiry(-100))


if __name__ == "__main__":
    unittest.main()
