"""Tests for member verification challenge helpers and router registration."""
import unittest
from unittest.mock import AsyncMock, patch

from aiogram.exceptions import TelegramForbiddenError

from app.handlers.verification import (
    _make_challenge, _permissions, create_verification_router,
    expire_member_verification,
)


class VerificationTests(unittest.TestCase):
    def test_challenge_has_four_choices_and_one_correct_answer(self) -> None:
        question, options, correct_index = _make_challenge()
        self.assertIn("What is", question)
        self.assertEqual(len(options), 4)
        self.assertEqual(len(set(options)), 4)
        left, right = [int(value) for value in question.removeprefix("What is ").rstrip("?").split(" + ")]
        self.assertEqual(options[correct_index], left + right)

    def test_restriction_disables_all_send_permissions(self) -> None:
        permissions = _permissions(False)
        for field in (
            "can_send_messages", "can_send_audios", "can_send_documents",
            "can_send_photos", "can_send_videos", "can_send_video_notes",
            "can_send_voice_notes", "can_send_polls", "can_send_other_messages",
            "can_add_web_page_previews",
        ):
            self.assertFalse(getattr(permissions, field))

    def test_restore_permissions_enables_all_send_permissions(self) -> None:
        permissions = _permissions(True)
        self.assertTrue(permissions.can_send_messages)
        self.assertTrue(permissions.can_send_photos)
        self.assertTrue(permissions.can_send_other_messages)

    async def test_expired_member_is_removed_and_state_is_deleted(self) -> None:
        bot = type("FakeBot", (), {})()
        bot.ban_chat_member = AsyncMock()
        bot.unban_chat_member = AsyncMock()
        with (
            patch("app.handlers.verification.delete_verification") as delete,
            patch("app.handlers.verification.record_audit_event") as audit,
            patch("app.handlers.verification.record_security_incident") as incident,
        ):
            result = await expire_member_verification(bot, -100, 7)
        self.assertTrue(result)
        bot.ban_chat_member.assert_awaited_once_with(
            chat_id=-100, user_id=7, revoke_messages=False
        )
        bot.unban_chat_member.assert_awaited_once_with(
            chat_id=-100, user_id=7, only_if_banned=True
        )
        delete.assert_called_once_with(-100, 7)
        audit.assert_called_once()
        incident.assert_called_once()

    async def test_failed_expiry_removal_keeps_state_for_retry(self) -> None:
        bot = type("FakeBot", (), {})()
        bot.ban_chat_member = AsyncMock(side_effect=TelegramForbiddenError(
            method="banChatMember", message="not enough rights"
        ))
        bot.unban_chat_member = AsyncMock()
        with patch("app.handlers.verification.delete_verification") as delete:
            result = await expire_member_verification(bot, -100, 7)
        self.assertFalse(result)
        delete.assert_not_called()
        bot.unban_chat_member.assert_not_awaited()

    def test_router_registers_only_verification_callback(self) -> None:
        router = create_verification_router()
        self.assertEqual(router.name, "member_verification")
        self.assertEqual(len(router.message.handlers), 0)
        self.assertEqual(len(router.callback_query.handlers), 1)


if __name__ == "__main__":
    unittest.main()
