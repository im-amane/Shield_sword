"""Unit tests for NVIDIA NIM safety parsing and request limits."""
import unittest

from app.ai_guard import AiScanLimiter, parse_safety_result


class AiGuardTests(unittest.TestCase):
    def test_parse_safe_result(self):
        self.assertEqual(
            parse_safety_result('{"User Safety":"safe"}'),
            {"unsafe": False, "categories": ""},
        )

    def test_parse_unsafe_result(self):
        self.assertEqual(
            parse_safety_result('{"User Safety":"unsafe","Safety Categories":"Fraud,Threat"}'),
            {"unsafe": True, "categories": "Fraud,Threat"},
        )

    def test_parse_json_embedded_in_model_text(self):
        self.assertTrue(parse_safety_result('result: {"User Safety":"unsafe"}')["unsafe"])

    def test_invalid_or_ambiguous_output_is_not_actionable(self):
        self.assertIsNone(parse_safety_result("unsafe"))
        self.assertIsNone(parse_safety_result('{"User Safety":"maybe"}'))
        self.assertIsNone(parse_safety_result('{"User Safety":"unsafe"'))

    def test_scan_limiter_enforces_user_chat_and_global_limits(self):
        limiter = AiScanLimiter()
        self.assertTrue(limiter.allow(-100, 1, now=10.0))
        self.assertFalse(limiter.allow(-100, 1, now=17.9))
        self.assertFalse(limiter.allow(-100, 2, now=10.1))
        self.assertTrue(limiter.allow(-100, 2, now=10.3))
        self.assertTrue(limiter.allow(-200, 3, now=10.6))


if __name__ == "__main__":
    unittest.main()
