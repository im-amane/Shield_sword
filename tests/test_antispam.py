"""Tests for anti-spam rate and duplicate detection."""
import unittest

from app.handlers.antispam import (
    MAX_MESSAGES_IN_WINDOW,
    _is_flooding,
    _message_times,
    _duplicate_times,
    _last_action,
    _muted_permissions,
)


class AntiSpamTests(unittest.TestCase):
    def setUp(self) -> None:
        _message_times.clear()
        _duplicate_times.clear()
        _last_action.clear()

    def test_rate_limit_triggers_after_six_messages_in_window(self) -> None:
        results = [
            _is_flooding(-100, 123, f"message {index}", 100.0 + index * 0.5)
            for index in range(MAX_MESSAGES_IN_WINDOW + 1)
        ]
        self.assertFalse(any(results[:-1]))
        self.assertTrue(results[-1])

    def test_repeated_identical_messages_trigger_detection(self) -> None:
        results = [
            _is_flooding(-100, 123, "buy followers", 200.0 + index)
            for index in range(3)
        ]
        self.assertEqual(results, [False, False, True])

    def test_old_messages_expire_from_window(self) -> None:
        _is_flooding(-100, 123, "first", 100.0)
        _is_flooding(-100, 123, "second", 101.0)
        self.assertFalse(_is_flooding(-100, 123, "third", 110.0))

    def test_mute_permissions_disable_sending(self) -> None:
        permissions = _muted_permissions()
        self.assertFalse(permissions.can_send_messages)
        self.assertFalse(permissions.can_send_photos)
        self.assertFalse(permissions.can_send_other_messages)


if __name__ == "__main__":
    unittest.main()
