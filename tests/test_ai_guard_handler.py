"""Handler-level regression tests for NVIDIA AI Guard moderation."""
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from aiogram.enums import ChatMemberStatus

from app.handlers.ai_guard import create_ai_guard_router


class AiGuardHandlerTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.client = SimpleNamespace(classify=AsyncMock(return_value={
            "unsafe": False, "categories": ""
        }))
        self.client_patch = patch(
            "app.handlers.ai_guard.NimSafetyClient", return_value=self.client
        )
        self.client_patch.start()
        self.addCleanup(self.client_patch.stop)

        self.limiter = SimpleNamespace(allow=Mock(return_value=True), allow_channel_post=Mock(return_value=True))
        self.limiter_patch = patch(
            "app.handlers.ai_guard.AiScanLimiter", return_value=self.limiter
        )
        self.limiter_patch.start()
        self.addCleanup(self.limiter_patch.stop)

        self.router = create_ai_guard_router(999, "guardian-key", "safety-model")
        self.handler = self.router.message.handlers[0].callback
        self.message = SimpleNamespace(
            from_user=SimpleNamespace(
                id=123, is_bot=False, full_name="Member", username="member"
            ),
            chat=SimpleNamespace(id=-100123, title="Test group"),
            text="A normal community message",
            caption=None,
            bot=SimpleNamespace(
                get_chat_member=AsyncMock(return_value=SimpleNamespace(
                    status=ChatMemberStatus.MEMBER
                )),
                restrict_chat_member=AsyncMock(),
            ),
            delete=AsyncMock(),
            answer=AsyncMock(),
        )

    async def test_safe_message_is_not_deleted_or_warned(self):
        with patch("app.handlers.ai_guard.add_warning") as warning:
            await self.handler(self.message)
        self.message.delete.assert_not_awaited()
        self.message.answer.assert_not_awaited()
        warning.assert_not_called()

    async def test_unsafe_message_is_deleted_and_audited(self):
        self.client.classify.return_value = {"unsafe": True, "categories": "Threat"}
        with patch("app.handlers.ai_guard.add_warning", return_value=1) as warning, \
             patch("app.handlers.ai_guard.record_audit_event") as audit, \
             patch("app.handlers.ai_guard.record_security_incident") as incident:
            await self.handler(self.message)
        self.message.delete.assert_awaited_once()
        warning.assert_called_once_with(-100123, 123)
        audit.assert_called_once()
        incident.assert_called_once()
        self.message.answer.assert_awaited_once()

    async def test_ai_provider_unavailable_does_not_delete_normal_message(self):
        self.client.classify.return_value = None
        with patch("app.handlers.ai_guard.add_warning") as warning:
            await self.handler(self.message)
        self.message.delete.assert_not_awaited()
        self.message.answer.assert_not_awaited()
        warning.assert_not_called()

    async def test_owner_is_exempt(self):
        self.message.from_user.id = 999
        await self.handler(self.message)
        self.message.bot.get_chat_member.assert_not_awaited()
        self.client.classify.assert_not_awaited()

    async def test_bot_messages_are_exempt(self):
        self.message.from_user.is_bot = True
        await self.handler(self.message)
        self.client.classify.assert_not_awaited()

    async def test_commands_are_exempt(self):
        self.message.text = "/help"
        await self.handler(self.message)
        self.client.classify.assert_not_awaited()

    async def test_administrators_are_exempt(self):
        self.message.bot.get_chat_member.return_value.status = ChatMemberStatus.ADMINISTRATOR
        await self.handler(self.message)
        self.client.classify.assert_not_awaited()
        self.message.delete.assert_not_awaited()

    async def test_scan_budget_skips_extra_provider_calls(self):
        self.limiter.allow.return_value = False
        await self.handler(self.message)
        self.message.bot.get_chat_member.assert_not_awaited()
        self.client.classify.assert_not_awaited()

    async def test_member_lookup_failure_does_not_trigger_ai_action(self):
        from aiogram.exceptions import TelegramNetworkError
        self.message.bot.get_chat_member.side_effect = TelegramNetworkError(
            method=Mock(), message="network unavailable"
        )
        await self.handler(self.message)
        self.client.classify.assert_not_awaited()
        self.message.delete.assert_not_awaited()

    async def test_safe_channel_post_is_not_deleted(self):
        handler = self.router.channel_post.handlers[0].callback
        post = SimpleNamespace(
            chat=SimpleNamespace(id=-100456, type="channel", title="Test channel"),
            text="A normal channel announcement", caption=None, message_id=77,
            delete=AsyncMock(),
        )
        await handler(post)
        self.client.classify.assert_awaited_once_with("A normal channel announcement")
        post.delete.assert_not_awaited()

    async def test_unsafe_channel_post_is_deleted_and_audited(self):
        handler = self.router.channel_post.handlers[0].callback
        self.client.classify.return_value = {"unsafe": True, "categories": "Phishing"}
        post = SimpleNamespace(
            chat=SimpleNamespace(id=-100456, type="channel", title="Test channel"),
            text=None, caption="Click this credential theft link",
            message_id=78, delete=AsyncMock(),
        )
        with patch("app.handlers.ai_guard.record_audit_event") as audit, \
             patch("app.handlers.ai_guard.record_security_incident") as incident:
            await handler(post)
        post.delete.assert_awaited_once()
        audit.assert_called_once()
        incident.assert_called_once()

    async def test_channel_scan_budget_skips_extra_provider_calls(self):
        self.limiter.allow_channel_post.return_value = False
        handler = self.router.channel_post.handlers[0].callback
        post = SimpleNamespace(
            chat=SimpleNamespace(id=-100456, type="channel", title="Test channel"),
            text="Ordinary announcement", caption=None, message_id=80,
            delete=AsyncMock(),
        )
        await handler(post)
        self.limiter.allow_channel_post.assert_called_once_with(-100456)
        self.client.classify.assert_not_awaited()
        post.delete.assert_not_awaited()

    async def test_channel_provider_failure_keeps_post(self):
        handler = self.router.channel_post.handlers[0].callback
        self.client.classify.return_value = None
        post = SimpleNamespace(
            chat=SimpleNamespace(id=-100456, type="channel", title="Test channel"),
            text="Ordinary announcement", caption=None, message_id=79,
            delete=AsyncMock(),
        )
        await handler(post)
        post.delete.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
