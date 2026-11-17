"""Tests for member verification challenge helpers and router registration."""
import unittest

from app.handlers.verification import (
    _make_challenge,
    _permissions,
    create_verification_router,
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

    def test_router_registers_join_and_callback_handlers(self) -> None:
        router = create_verification_router()
        self.assertEqual(router.name, "member_verification")
        self.assertEqual(len(router.message.handlers), 1)
        self.assertEqual(len(router.callback_query.handlers), 1)


if __name__ == "__main__":
    unittest.main()
