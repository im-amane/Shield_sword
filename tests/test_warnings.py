"""Unit tests for warning-count helpers."""
import unittest

from app.handlers.warnings import (
    WARN_LIMIT,
    add_warning,
    get_warnings,
    reset_warnings,
)


class WarningCountTests(unittest.TestCase):
    def setUp(self) -> None:
        reset_warnings(-100, -100)

    def test_warning_count_increments_per_chat_and_user(self) -> None:
        self.assertEqual(add_warning(-100, -100), 1)
        self.assertEqual(add_warning(-100, -100), 2)
        self.assertEqual(get_warnings(-100, -100), 2)
        self.assertEqual(get_warnings(-100, 55), 0)
        self.assertEqual(get_warnings(-200, -100), 0)

    def test_threshold_is_three(self) -> None:
        self.assertEqual(WARN_LIMIT, 3)
        self.assertEqual(add_warning(-100, -100), 1)
        self.assertEqual(add_warning(-100, -100), 2)
        self.assertEqual(add_warning(-100, -100), 3)

    def test_reset_clears_warning_count(self) -> None:
        add_warning(-100, -100)
        reset_warnings(-100, -100)
        self.assertEqual(get_warnings(-100, -100), 0)


if __name__ == "__main__":
    unittest.main()
