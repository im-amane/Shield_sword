"""Tests for bounded NVIDIA NIM request handling."""
import unittest
from unittest.mock import patch

from app.nvidia_nim import request_nim_completion


class NvidiaNimTests(unittest.TestCase):
    def test_missing_key_fails_without_network(self):
        result = request_nim_completion("", "model", [])
        self.assertEqual(result.error, "missing_configuration")

    @patch("app.nvidia_nim.urllib.request.urlopen")
    def test_valid_chat_completion(self, mocked):
        class Response:
            status = 200
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
            def read(self, limit):
                return b'{"choices":[{"message":{"content":"hello"}}]}'
        mocked.return_value = Response()
        result = request_nim_completion("secret", "model", [{"role": "user", "content": "hi"}])
        self.assertEqual(result.text, "hello")
        self.assertIsNone(result.error)
        args, kwargs = mocked.call_args
        self.assertNotIn("secret", repr(args[0].headers))
        self.assertLessEqual(kwargs["timeout"], 8.0)

    @patch("app.nvidia_nim.urllib.request.urlopen")
    def test_http_error_is_sanitized(self, mocked):
        import urllib.error
        mocked.side_effect = urllib.error.HTTPError(
            "https://example.invalid", 429, "rate limited", {}, None
        )
        result = request_nim_completion("secret", "model", [{"role": "user", "content": "hi"}])
        self.assertEqual(result.error, "http_429")
        self.assertIsNone(result.text)

    @patch("app.nvidia_nim.urllib.request.urlopen")
    def test_invalid_response_is_rejected(self, mocked):
        class Response:
            status = 200
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
            def read(self, limit):
                return b'{"choices":[]}'
        mocked.return_value = Response()
        result = request_nim_completion("secret", "model", [{"role": "user", "content": "hi"}])
        self.assertEqual(result.error, "invalid_response")


if __name__ == "__main__":
    unittest.main()
