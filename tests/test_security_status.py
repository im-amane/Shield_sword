"""Tests for unified group security status output."""
import unittest
from unittest.mock import patch

from app.handlers.security_status import security_status_text


class SecurityStatusTests(unittest.TestCase):
    @patch("app.handlers.security_status.is_copyright_enabled", return_value=True)
    @patch("app.handlers.security_status.is_feature_enabled")
    def test_status_reports_each_configurable_filter(self, feature_enabled, copyright_enabled):
        feature_enabled.side_effect = lambda feature, chat_id: feature == "antilink"
        text = security_status_text(-100, "Ani World Main")
        self.assertIn("Ani World Main", text)
        self.assertIn("Anti-link:", text)
        self.assertIn("Bad-word filter:", text)
        self.assertIn("Media upload policy:", text)
        self.assertIn("New-member CAPTCHA:", text)
        self.assertIn("Anti-spam:", text)
        self.assertIn("Raid detection:", text)
        feature_enabled.assert_any_call("antilink", -100)
        feature_enabled.assert_any_call("badwords", -100)
        copyright_enabled.assert_called_once_with(-100)

    @patch("app.handlers.security_status.is_copyright_enabled", return_value=False)
    @patch("app.handlers.security_status.is_feature_enabled", return_value=False)
    def test_disabled_features_are_visible(self, feature_enabled, copyright_enabled):
        text = security_status_text(-200, "Test Group")
        self.assertIn("Anti-link:", text)
        self.assertIn("Bad-word filter:", text)
        self.assertIn("Media upload policy:", text)


if __name__ == "__main__":
    unittest.main()
