"""Tests for passive community discovery."""
import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from aiogram.enums import ChatType

from app.group_registry import GroupRegistryMiddleware


class GroupRegistryMiddlewareTests(unittest.TestCase):
    def test_registers_group_before_handler_even_for_commands(self):
        middleware = GroupRegistryMiddleware()
        message = SimpleNamespace(
            chat=SimpleNamespace(id=-100123, title="Ani World", type=ChatType.SUPERGROUP)
        )
        handler = AsyncMock(return_value="handled")

        async def run():
            with patch("app.group_registry.register_group") as register:
                result = await middleware(handler, message, {})
                register.assert_called_once_with(-100123, "Ani World")
                self.assertEqual(result, "handled")
            handler.assert_awaited_once_with(message, {})

        asyncio.run(run())

    def test_does_not_register_private_chats(self):
        middleware = GroupRegistryMiddleware()
        message = SimpleNamespace(
            chat=SimpleNamespace(id=123, title=None, type=ChatType.PRIVATE)
        )
        handler = AsyncMock(return_value="handled")

        async def run():
            with patch("app.group_registry.register_group") as register:
                await middleware(handler, message, {})
                register.assert_not_called()
            handler.assert_awaited_once_with(message, {})

        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
