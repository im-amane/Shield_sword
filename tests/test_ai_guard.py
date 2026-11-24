"""Unit tests for NVIDIA NIM safety parsing and request limits."""
import unittest
from unittest.mock import patch
import urllib.error

from app.ai_guard import AiScanLimiter, NimSafetyClient, parse_safety_result


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

    def test_safety_client_allows_twenty_second_timeout_and_caps_it(self):
        self.assertEqual(NimSafetyClient("key", timeout=20.0).timeout, 20.0)
        self.assertEqual(NimSafetyClient("key", timeout=30.0).timeout, 20.0)
        self.assertEqual(NimSafetyClient("key").timeout, 20.0)

    def test_scan_limiter_enforces_user_chat_and_global_limits(self):
        limiter = AiScanLimiter()
        self.assertTrue(limiter.allow(-100, 1, now=10.0))
        self.assertFalse(limiter.allow(-100, 1, now=17.9))
        self.assertFalse(limiter.allow(-100, 2, now=10.1))
        self.assertTrue(limiter.allow(-100, 2, now=10.3))
        self.assertTrue(limiter.allow(-200, 3, now=10.6))

    def test_safety_client_retries_transient_gateway_failure_once(self):
        client = NimSafetyClient("guardian-key")
        error = urllib.error.HTTPError(
            "https://example.invalid", 502, "bad gateway", {}, None
        )
        good_payload = {
            "choices": [{"message": {"content": '{"User Safety":"safe"}'}}]
        }

        class FakeResponse:
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
            def read(self, _limit):
                import json
                return json.dumps(good_payload).encode()

        with patch("app.ai_guard.urllib.request.urlopen", side_effect=[error, FakeResponse()]) as call:
            with patch("app.ai_guard.time.sleep"):
                result = client._classify_sync("hello")
        self.assertEqual(result, {"unsafe": False, "categories": ""})
        self.assertEqual(call.call_count, 2)


if __name__ == "__main__":
    unittest.main()
