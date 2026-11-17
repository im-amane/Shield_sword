"""Tests for fail-closed owner authorization."""
import unittest

from app.security.owner import is_owner


class OwnerAuthorizationTests(unittest.TestCase):
    def test_matching_id_is_authorized(self) -> None:
        self.assertTrue(is_owner(8891272628, 8891272628))

    def test_different_id_is_rejected(self) -> None:
        self.assertFalse(is_owner(123456789, 8891272628))

    def test_missing_user_is_rejected(self) -> None:
        self.assertFalse(is_owner(None, 8891272628))

    def test_missing_owner_configuration_fails_closed(self) -> None:
        self.assertFalse(is_owner(8891272628, None))

    def test_invalid_non_positive_ids_are_rejected(self) -> None:
        self.assertFalse(is_owner(0, 8891272628))
        self.assertFalse(is_owner(8891272628, 0))
        self.assertFalse(is_owner(-1, 8891272628))


if __name__ == "__main__":
    unittest.main()
