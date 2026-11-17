"""Unit tests for anti-link URL policy helpers."""
import unittest

from app.handlers.antilink import is_allowed_link, normalize_domain


class AntiLinkPolicyTests(unittest.TestCase):
    def test_normalize_domain_accepts_domain_and_url(self) -> None:
        self.assertEqual(normalize_domain("Example.COM"), "example.com")
        self.assertEqual(normalize_domain("https://www.Example.com/path"), "example.com")

    def test_normalize_domain_rejects_invalid_input(self) -> None:
        with self.assertRaises(ValueError):
            normalize_domain("not a domain")

    def test_allowlist_matches_domain_and_subdomains(self) -> None:
        allowed = {"example.com"}
        self.assertTrue(is_allowed_link("https://example.com/page", allowed))
        self.assertTrue(is_allowed_link("sub.example.com/path", allowed))
        self.assertFalse(is_allowed_link("https://notexample.com", allowed))

    def test_telegram_invites_are_never_allowlisted(self) -> None:
        self.assertFalse(is_allowed_link("https://t.me/example", {"t.me"}))
        self.assertFalse(is_allowed_link("telegram.me/+invite", set()))


if __name__ == "__main__":
    unittest.main()
