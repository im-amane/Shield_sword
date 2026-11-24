"""Tests for the owner-only AI safety endpoint diagnostic."""
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from aiogram.enums import ChatType
from app.handlers.owner import create_owner_router


class OwnerAiDiagnosticTests(unittest.IsolatedAsyncioTestCase):
    async def test_aitest_awaits_classifier_and_reports_pass(self):
        router = create_owner_router(12345, "test-key", "test-model")
        handler = next(item.callback for item in router.message.handlers
                       if getattr(item.callback, "__name__", "") == "ai_test_command")
        client = SimpleNamespace(classify=AsyncMock(return_value={
            "unsafe": False, "categories": ""
        }))
        message = SimpleNamespace(
            chat=SimpleNamespace(type=ChatType.PRIVATE),
            from_user=SimpleNamespace(id=12345),
            answer=AsyncMock(return_value=SimpleNamespace(edit_text=AsyncMock())),
        )
        with patch("app.handlers.owner.NimSafetyClient", return_value=client), \
             patch("app.handlers.owner.send_category_card", new=AsyncMock()):
            await handler(message)
        client.classify.assert_awaited_once()
        message.answer.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
