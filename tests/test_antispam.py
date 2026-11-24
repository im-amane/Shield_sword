"""Tests for persistent anti-spam detection and mute coordination."""
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from app import storage
from app.handlers.antispam import (
    DUPLICATE_WINDOW_SECONDS,
    MAX_IDENTICAL_MESSAGES,
    MAX_MESSAGES_IN_WINDOW,
    MUTE_SECONDS,
    WINDOW_SECONDS,
    _is_privileged_member,
    _muted_permissions,
)


class AntiSpamTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "antispam.sqlite3"
        self.path_patch = patch.object(storage, "DB_PATH", self.db_path)
        self.path_patch.start()
        storage._initialized_path = None
        storage.init_storage()

    def tearDown(self) -> None:
        storage._initialized_path = None
        self.path_patch.stop()
        self.temp_dir.cleanup()

    def _record(self, fingerprint: str, now: float) -> bool:
        return storage.record_antispam_message(
            -100,
            123,
            fingerprint,
            now,
            WINDOW_SECONDS,
            DUPLICATE_WINDOW_SECONDS,
            MAX_MESSAGES_IN_WINDOW,
            MAX_IDENTICAL_MESSAGES,
        )

    def test_rate_limit_triggers_after_six_messages_in_window(self) -> None:
        results = [
            self._record(f"message {index}", 100.0 + index * 0.5)
            for index in range(MAX_MESSAGES_IN_WINDOW + 1)
        ]
        self.assertFalse(any(results[:-1]))
        self.assertTrue(results[-1])

    def test_repeated_identical_messages_trigger_detection(self) -> None:
        results = [
            self._record("buy followers", 200.0 + index)
            for index in range(MAX_IDENTICAL_MESSAGES)
        ]
        self.assertEqual(results, [False, False, True])

    def test_old_messages_expire_from_rate_window(self) -> None:
        self._record("first", 100.0)
        self._record("second", 101.0)
        self.assertFalse(self._record("third", 110.0))

    def test_message_history_survives_storage_reinitialization(self) -> None:
        self._record("persistent duplicate", 200.0)
        self._record("persistent duplicate", 201.0)
        storage._initialized_path = None
        storage.init_storage()
        self.assertTrue(self._record("persistent duplicate", 202.0))

    def test_mute_cooldown_persists_and_claim_is_single_winner(self) -> None:
        now = 1_000.0
        self.assertTrue(storage.claim_antispam_mute(-100, 123, now, MUTE_SECONDS))
        self.assertEqual(
            storage.get_antispam_mute_until(-100, 123),
            now + MUTE_SECONDS,
        )
        storage._initialized_path = None
        storage.init_storage()
        self.assertFalse(storage.claim_antispam_mute(-100, 123, now + 1, MUTE_SECONDS))
        self.assertEqual(storage.get_antispam_mute_until(-100, 123), now + MUTE_SECONDS)

    def test_concurrent_mute_claims_only_allow_one_restriction(self) -> None:
        now = 2_000.0
        with ThreadPoolExecutor(max_workers=8) as executor:
            results = list(executor.map(
                lambda _: storage.claim_antispam_mute(-200, 456, now, MUTE_SECONDS),
                range(8),
            ))
        self.assertEqual(sum(results), 1)

    def test_privileged_member_status_supports_raw_strings(self) -> None:
        self.assertTrue(_is_privileged_member(type("Member", (), {"status": "administrator"})()))
        self.assertTrue(_is_privileged_member(type("Member", (), {"status": "creator"})()))
        self.assertFalse(_is_privileged_member(type("Member", (), {"status": "member"})()))

    def test_mute_permissions_disable_sending(self) -> None:
        permissions = _muted_permissions()
        self.assertFalse(permissions.can_send_messages)
        self.assertFalse(permissions.can_send_photos)
        self.assertFalse(permissions.can_send_other_messages)


if __name__ == "__main__":
    unittest.main()
