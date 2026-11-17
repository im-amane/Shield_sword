"""Join verification with a short arithmetic captcha."""
from __future__ import annotations

import asyncio
import logging
import secrets
import time

from aiogram import F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.types import (
    CallbackQuery,
    ChatPermissions,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    User,
)

from app.handlers.typography import premium_text
from app.storage import delete_verification, get_expired_verifications, get_verification, save_verification

logger = logging.getLogger(__name__)
CHALLENGE_TTL_SECONDS = 180
EXPIRY_CHECK_INTERVAL_SECONDS = 10

_SEND_PERMISSION_FIELDS = (
    "can_send_messages",
    "can_send_audios",
    "can_send_documents",
    "can_send_photos",
    "can_send_videos",
    "can_send_video_notes",
    "can_send_voice_notes",
    "can_send_polls",
    "can_send_other_messages",
    "can_add_web_page_previews",
)


def _permissions(allowed: bool) -> ChatPermissions:
    """Build a complete send-permission set for restricting/restoring a member."""
    return ChatPermissions(**{field: allowed for field in _SEND_PERMISSION_FIELDS})


async def expire_member_verification(bot, chat_id: int, user_id: int) -> bool:
    """Remove a member who did not complete the CAPTCHA before its deadline."""
    try:
        await bot.ban_chat_member(
            chat_id=chat_id,
            user_id=user_id,
            revoke_messages=False,
        )
        await bot.unban_chat_member(
            chat_id=chat_id,
            user_id=user_id,
            only_if_banned=True,
        )
        delete_verification(chat_id, user_id)
        logger.info(
            "Removed unverified member user_id=%s chat_id=%s",
            user_id, chat_id,
        )
        return True
    except TelegramAPIError:
        # Keep the row so the background worker can retry after a transient API failure.
        logger.exception(
            "Could not remove expired unverified member user_id=%s chat_id=%s",
            user_id, chat_id,
        )
        return False


async def verification_expiry_loop(bot) -> None:
    """Enforce expired challenges, including records surviving a service restart."""
    while True:
        expired = get_expired_verifications(int(time.time()))
        for item in expired:
            await expire_member_verification(
                bot, item["chat_id"], item["user_id"]
            )
        await asyncio.sleep(EXPIRY_CHECK_INTERVAL_SECONDS)


def _make_challenge() -> tuple[str, list[int], int]:
    """Return a simple addition question, shuffled choices, and correct choice index."""
    left = secrets.randbelow(8) + 2
    right = secrets.randbelow(8) + 2
    answer = left + right
    options = list({answer, answer + 1, answer - 1, answer + 2})
    secrets.SystemRandom().shuffle(options)
    return f"What is {left} + {right}?", options, options.index(answer)


async def start_member_verification(message: Message, members: list[User]) -> None:
    """Restrict new members and send their captcha from the shared join handler."""
    chat_id = message.chat.id
    now = int(time.time())

    for member in members:
        if member.is_bot:
            continue
        try:
            member_status = await message.bot.get_chat_member(chat_id, member.id)
            if member_status.status in ("creator", "administrator"):
                continue

            bot_identity = await message.bot.get_me()
            bot_status = await message.bot.get_chat_member(chat_id, bot_identity.id)
            if bot_status.status != "administrator" or not getattr(
                bot_status, "can_restrict_members", False
            ):
                logger.warning(
                    "Verification skipped: bot lacks restrict permission in chat_id=%s",
                    chat_id,
                )
                await message.answer(
                    premium_text("⚠️ Member verification is not active: please make the bot an administrator with <b>Ban users</b> permission. 🛡️")
                )
                continue

            chat = await message.bot.get_chat(chat_id)
            original_permissions = chat.permissions or _permissions(True)
            expires_at = now + CHALLENGE_TTL_SECONDS
            await message.bot.restrict_chat_member(
                chat_id=chat_id,
                user_id=member.id,
                permissions=_permissions(False),
                # Keep the member restricted until a correct answer or expiry enforcement.
            )

            question, options, correct_index = _make_challenge()
            save_verification(
                chat_id,
                member.id,
                correct_index,
                expires_at,
                original_permissions.model_dump(exclude_none=True),
            )
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text=str(option),
                            callback_data=f"verify:{chat_id}:{member.id}:{index}",
                        )
                        for index, option in enumerate(options)
                    ]
                ]
            )
            await message.answer(premium_text(
                f"⛩️ Hey <a href=\"tg://user?id={member.id}\">{member.full_name}</a>!\n\n"
                "Before joining the conversation, complete this little security challenge.\n\n"
                f"🧩 <b>{question}</b>\n\n"
                "⏳ You have 3 minutes to verify and unlock the chat."),
                reply_markup=keyboard,
            )
        except TelegramAPIError:
            logger.exception(
                "Could not start verification for user_id=%s chat_id=%s",
                member.id,
                chat_id,
            )


def create_verification_router() -> Router:
    """Create callback handlers; join processing is shared with the welcome handler."""
    router = Router(name="member_verification")

    @router.callback_query(F.data.startswith("verify:"))
    async def verify_callback(callback: CallbackQuery) -> None:
        try:
            _, raw_chat_id, raw_user_id, raw_index = (callback.data or "").split(":")
            chat_id, user_id, selected_index = (
                int(raw_chat_id),
                int(raw_user_id),
                int(raw_index),
            )
        except (TypeError, ValueError):
            await callback.answer(premium_text("Ye button valid nahi hai. Dobara try karo. 😅"), show_alert=True)
            return

        if (
            callback.from_user.id != user_id
            or not callback.message
            or callback.message.chat.id != chat_id
        ):
            await callback.answer(premium_text("Ye verification kisi aur member ke liye hai. 🙂"), show_alert=True)
            return

        state = get_verification(chat_id, user_id)
        if not state or int(state["expires_at"]) <= int(time.time()):
            removed = await expire_member_verification(
                callback.bot, chat_id, user_id
            )
            if removed:
                await callback.answer(
                    premium_text("⏳ Verification expired. You were removed from the group; rejoin to try again."),
                    show_alert=True,
                )
            else:
                await callback.answer(
                    premium_text("⏳ Verification expired, but removal failed. Please contact a group admin."),
                    show_alert=True,
                )
            return

        if selected_index != int(state["correct_index"]):
            await callback.answer(premium_text("Not quite! Give it another try. 😊"), show_alert=True)
            return

        try:
            await callback.bot.restrict_chat_member(
                chat_id=chat_id,
                user_id=user_id,
                permissions=ChatPermissions(**state["permissions"]),
            )
            delete_verification(chat_id, user_id)
            await callback.message.edit_text(premium_text(
                f"✅ <a href=\"tg://user?id={user_id}\">Member</a> verified!\n\n"
                "You're all set. Welcome to the community! 🎉"
            ))
            await callback.answer(premium_text("Verified! Welcome in. 🎉"))
            logger.info("Verified user_id=%s chat_id=%s", user_id, chat_id)
        except TelegramAPIError:
            logger.exception("Could not complete verification for user_id=%s", user_id)
            await callback.answer(premium_text("We couldn’t complete verification. Please contact a group admin. 🛠️"), show_alert=True)

    return router
