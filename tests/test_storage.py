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

    def test_group_dashboard_summary_is_scoped_and_read_only(self) -> None:
        import time

        storage.register_group(-100, "Ani World")
        storage.register_group(-200, "Other Group")
        storage.set_feature_enabled("antilink", -100, False)
        storage.add_badword(-100, "spoiler")
        storage.add_allowed_domain(-100, "example.com")
        storage.set_raid_expiry(-100, time.time() + 120)
        storage.save_verification(-100, 7, 2, int(time.time()) + 60, {})
        storage.record_member_join(-100, "Ani World", 7, "member", "Member")
        storage.record_security_incident(-100, "Ani World", "anti_spam")

        summary = storage.get_group_protection_summary(-100)
        self.assertIsNotNone(summary)
        self.assertEqual(summary["title"], "Ani World")
        self.assertFalse(summary["antilink_enabled"])
        self.assertTrue(summary["badwords_enabled"])
        self.assertTrue(summary["copyright_enabled"])
        self.assertEqual(summary["badword_count"], 1)
        self.assertEqual(summary["allowed_domain_count"], 1)
        self.assertEqual(summary["pending_verifications"], 1)
        self.assertTrue(summary["active_raid"])
        self.assertEqual(summary["joins_24h"], 1)
        self.assertEqual(summary["incidents_24h"], 1)

        other = storage.get_group_protection_summary(-200)
        self.assertTrue(other["antilink_enabled"])
        self.assertEqual(other["badword_count"], 0)
        self.assertEqual(other["allowed_domain_count"], 0)
        self.assertEqual(other["pending_verifications"], 0)
        self.assertFalse(other["active_raid"])
        self.assertEqual(other["joins_24h"], 0)
        self.assertEqual(other["incidents_24h"], 0)
        self.assertIsNone(storage.get_group_protection_summary(-300))

    def test_known_group_pages_are_bounded_and_counted(self) -> None:
        for chat_id in range(-100, -112, -1):
            storage.register_group(chat_id, f"Group {chat_id}")
        self.assertEqual(storage.get_known_groups_count(), 12)
        self.assertEqual(len(storage.get_known_groups_page(5, 0)), 5)
        self.assertEqual(len(storage.get_known_groups_page(5, 5)), 5)
        self.assertEqual(len(storage.get_known_groups_page(5, 10)), 2)
        self.assertEqual(storage.get_known_groups_page(5, -10), storage.get_known_groups_page(5, 0))

    def test_verification_challenge_persists_and_expires(self) -> None:
        permissions = {"can_send_messages": False}
        storage.save_verification(-100, 7, 2, 500, permissions)
        self.assertEqual(
            storage.get_verification(-100, 7),
            {"correct_index": 2, "expires_at": 500, "permissions": permissions, "attempts": 0},
        )
        self.assertEqual(
            storage.get_expired_verifications(500),
            [{"chat_id": -100, "user_id": 7, "expires_at": 500}],
        )
        self.assertEqual(storage.get_expired_verifications(499), [])
        self.assertEqual(storage.increment_verification_attempt(-100, 7), 1)
        self.assertEqual(storage.increment_verification_attempt(-100, 7), 2)
        self.assertEqual(storage.increment_verification_attempt(-200, 7), 0)
        self.assertEqual(storage.get_verification(-100, 7)["attempts"], 2)
        storage.save_verification(-100, 7, 1, 600, permissions)
        self.assertEqual(storage.get_verification(-100, 7)["attempts"], 0)
        storage.cleanup_verifications(600)
        self.assertIsNone(storage.get_verification(-100, 7))

    def test_security_audit_is_bounded_and_readable(self) -> None:
        storage.record_audit_event(-100, "ban", 7, 8, "manual action")
        events = storage.get_audit_events(10)
        self.assertEqual(events[0]["action"], "ban")
        self.assertEqual(events[0]["actor_id"], 7)
        self.assertEqual(events[0]["target_id"], 8)
        self.assertEqual(events[0]["details"], "manual action")

    def test_security_metadata_is_single_line_bounded_and_safe(self) -> None:
        hostile = "first line\r\nFORGED EVENT\x00\x01 second line"
        storage.record_audit_event(-100, "audit\r\ninjection", details=hostile)
        storage.record_security_incident(
            -100, "Group\r\nFORGED", "incident\nforged",
            details=hostile, username="user\r\nforged",
        )
        audit = storage.get_audit_events(1)[0]
        incident = storage.get_recent_security_incidents(1)[0]
        self.assertNotIn("\n", audit["action"])
        self.assertNotIn("\r", audit["action"])
        self.assertNotIn("\n", audit["details"])
        self.assertNotIn("\r", audit["details"])
        self.assertNotIn("\x00", audit["details"])
        self.assertNotIn("\x01", audit["details"])
        self.assertNotIn("\n", incident["chat_title"])
        self.assertNotIn("\n", incident["kind"])
        self.assertNotIn("\n", incident["username"])
        self.assertLessEqual(len(audit["details"]), 500)

    def test_copyright_protection_defaults_on_and_can_be_toggled(self) -> None:
        self.assertTrue(storage.is_copyright_enabled(-100))
        storage.set_copyright_enabled(-100, False)
        self.assertFalse(storage.is_copyright_enabled(-100))
        storage.set_copyright_enabled(-100, True)
        self.assertTrue(storage.is_copyright_enabled(-100))

    def test_channel_media_protection_is_opt_in_and_persists(self) -> None:
        self.assertFalse(storage.is_channel_media_enabled(-100123))
        storage.set_channel_media_enabled(-100123, True)
        self.assertTrue(storage.is_channel_media_enabled(-100123))
        storage.set_channel_media_enabled(-100123, False)
        self.assertFalse(storage.is_channel_media_enabled(-100123))

    def test_backup_includes_persistent_antispam_tables_and_state(self) -> None:
        import sqlite3

        storage.record_antispam_message(-100, 7, "fingerprint", 1000.0, 8, 20, 6, 3)
        storage.claim_antispam_mute(-100, 7, 1000.0, 60)
        snapshot = storage.create_database_backup()
        with tempfile.TemporaryDirectory() as restore_dir:
            restored_path = Path(restore_dir) / "restored.sqlite3"
            restored_path.write_bytes(snapshot)
            restored = sqlite3.connect(restored_path)
            try:
                message_count = restored.execute(
                    "SELECT COUNT(*) FROM antispam_messages WHERE chat_id=? AND user_id=?",
                    (-100, 7),
                ).fetchone()[0]
                mute_until = restored.execute(
                    "SELECT muted_until FROM antispam_mutes WHERE chat_id=? AND user_id=?",
                    (-100, 7),
                ).fetchone()[0]
            finally:
                restored.close()
        self.assertEqual(message_count, 1)
        self.assertEqual(mute_until, 1060.0)
        self.assertEqual(storage.verify_database_backup(snapshot)["integrity"], "ok")

    def test_database_backup_is_valid_sqlite(self) -> None:
        storage.record_audit_event(-100, "restore_test", 7, 8, "round-trip")
        backup = storage.create_database_backup()
        self.assertTrue(backup.startswith(b"SQLite format 3"))
        restored_status = storage.verify_database_backup(backup)
        self.assertEqual(restored_status["integrity"], "ok")
        self.assertGreaterEqual(restored_status["table_count"], 10)
        import sqlite3
        with tempfile.TemporaryDirectory() as restore_dir:
            restored_path = Path(restore_dir) / "restored.sqlite3"
            restored_path.write_bytes(backup)
            restored = sqlite3.connect(restored_path)
            try:
                row = restored.execute(
                    "SELECT action, details FROM security_audit WHERE action='restore_test'"
                ).fetchone()
                self.assertEqual(row, ("restore_test", "round-trip"))
            finally:
                restored.close()
        status = storage.get_database_status()
        self.assertEqual(status["integrity"], "ok")
        self.assertTrue(status["exists"])
        self.assertGreaterEqual(status["table_count"], 10)

    def test_database_backup_rejects_corrupt_snapshot(self) -> None:
        import sqlite3
        with self.assertRaises(sqlite3.DatabaseError):
            storage.verify_database_backup(b"not a database")

    def test_database_backup_rejects_missing_application_table(self) -> None:
        import sqlite3
        snapshot = storage.create_database_backup()
        with tempfile.TemporaryDirectory() as restore_dir:
            restored_path = Path(restore_dir) / "incomplete.sqlite3"
            restored_path.write_bytes(snapshot)
            restored = sqlite3.connect(restored_path)
            try:
                restored.execute("PRAGMA journal_mode=DELETE")
                restored.execute("DROP TABLE badwords")
                restored.commit()
            finally:
                restored.close()
            with self.assertRaisesRegex(sqlite3.DatabaseError, "badwords"):
                storage.verify_database_backup(restored_path.read_bytes())

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
        self.assertTrue(storage.has_recent_security_incident(-100, "raid_detected", 600))
        self.assertFalse(storage.has_recent_security_incident(-200, "raid_detected", 600))

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
