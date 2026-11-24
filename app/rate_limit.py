"""Inbound request rate limiting for command and callback traffic.

Ordinary group messages remain governed by the dedicated anti-spam handler.
This middleware protects command handlers and callback-driven panels from
accidental loops and abusive request bursts without imposing a low group-wide
limit on normal conversation.
"""
from __future__ import annotations

import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message

logger = logging.getLogger(__name__)

# Per-member token buckets: initial burst, then steady refill rate.
COMMAND_CAPACITY = 5.0
COMMAND_REFILL_PER_SECOND = 0.5       # 5 burst; then 1 command / 2 seconds
CALLBACK_CAPACITY = 10.0
CALLBACK_REFILL_PER_SECOND = 1.0      # 10 burst; then 1 callback / second

# Shared group ceilings are intentionally much higher than a single member's
# allowance so 500 members can use the bot without competing at normal rates.
GROUP_COMMAND_CAPACITY = 60.0
GROUP_COMMAND_REFILL_PER_SECOND = 6.0
GROUP_CALLBACK_CAPACITY = 120.0
GROUP_CALLBACK_REFILL_PER_SECOND = 12.0

STATE_TTL_SECONDS = 180.0
MAX_BUCKETS = 20_000
NOTICE_COOLDOWN_SECONDS = 5.0


class TokenBucketLimiter:
    """Small bounded in-process token-bucket limiter."""

    def __init__(self, *, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._buckets: dict[tuple[Any, ...], tuple[float, float]] = {}
        self._calls = 0

    def allow(
        self,
        key: tuple[Any, ...],
        *,
        capacity: float,
        refill_per_second: float,
    ) -> bool:
        now = self._clock()
        tokens, updated = self._buckets.get(key, (capacity, now))
        tokens = min(capacity, tokens + max(0.0, now - updated) * refill_per_second)
        allowed = tokens >= 1.0
        if allowed:
            tokens -= 1.0
        self._buckets[key] = (tokens, now)

        self._calls += 1
        if self._calls % 256 == 0:
            cutoff = now - STATE_TTL_SECONDS
            self._buckets = {
                bucket_key: state
                for bucket_key, state in self._buckets.items()
                if state[1] >= cutoff
            }
            if len(self._buckets) > MAX_BUCKETS:
                oldest = sorted(self._buckets.items(), key=lambda item: item[1][1])
                for bucket_key, _ in oldest[: len(self._buckets) - MAX_BUCKETS]:
                    self._buckets.pop(bucket_key, None)
        return allowed


class RequestLimitMiddleware(BaseMiddleware):
    """Limit command/callback request bursts per user and per group."""

    def __init__(self, owner_id: int | None = None) -> None:
        self.owner_id = owner_id
        self.limiter = TokenBucketLimiter()
        self._notice_at: dict[tuple[int, int], float] = {}

    async def __call__(
        self,
        handler: Callable[[Any, dict[str, Any]], Awaitable[Any]],
        event: Any,
        data: dict[str, Any],
    ) -> Any:
        if isinstance(event, Message):
            text = event.text or ""
            if not text.startswith("/"):
                return await handler(event, data)
            user = event.from_user
            if user is None or (self.owner_id is not None and user.id == self.owner_id):
                return await handler(event, data)
            chat_id = event.chat.id
            user_id = user.id
            allowed = self.limiter.allow(
                ("command-user", chat_id, user_id),
                capacity=COMMAND_CAPACITY,
                refill_per_second=COMMAND_REFILL_PER_SECOND,
            )
            if allowed and event.chat.type in {"group", "supergroup"}:
                allowed = self.limiter.allow(
                    ("command-chat", chat_id),
                    capacity=GROUP_COMMAND_CAPACITY,
                    refill_per_second=GROUP_COMMAND_REFILL_PER_SECOND,
                )
            if not allowed:
                logger.warning(
                    "Command rate limit exceeded chat_id=%s user_id=%s",
                    chat_id, user_id,
                )
                return None
            return await handler(event, data)

        if isinstance(event, CallbackQuery):
            user = event.from_user
            if user is None or (self.owner_id is not None and user.id == self.owner_id):
                return await handler(event, data)
            chat = event.message.chat if event.message is not None else None
            chat_id = chat.id if chat is not None else 0
            allowed = self.limiter.allow(
                ("callback-user", chat_id, user.id),
                capacity=CALLBACK_CAPACITY,
                refill_per_second=CALLBACK_REFILL_PER_SECOND,
            )
            if allowed and chat is not None and chat.type in {"group", "supergroup"}:
                allowed = self.limiter.allow(
                    ("callback-chat", chat_id),
                    capacity=GROUP_CALLBACK_CAPACITY,
                    refill_per_second=GROUP_CALLBACK_REFILL_PER_SECOND,
                )
            if not allowed:
                logger.warning(
                    "Callback rate limit exceeded chat_id=%s user_id=%s",
                    chat_id, user.id,
                )
                now = time.monotonic()
                notice_key = (chat_id, user.id)
                if now - self._notice_at.get(notice_key, 0.0) >= NOTICE_COOLDOWN_SECONDS:
                    self._notice_at[notice_key] = now
                    try:
                        await event.answer("Too many requests. Please slow down.")
                    except Exception:
                        logger.debug("Could not acknowledge rate-limited callback", exc_info=True)
                if len(self._notice_at) > MAX_BUCKETS:
                    cutoff = now - STATE_TTL_SECONDS
                    self._notice_at = {
                        key: stamp for key, stamp in self._notice_at.items()
                        if stamp >= cutoff
                    }
                return None
            return await handler(event, data)

        return await handler(event, data)
