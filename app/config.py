"""Environment-backed application configuration."""
from __future__ import annotations

import os
from dataclasses import dataclass

from app.ai_chat import DEFAULT_NIM_CHAT_MODEL
from app.ai_guard import DEFAULT_NIM_MODEL


class ConfigurationError(RuntimeError):
    """Raised when required application configuration is missing or invalid."""


@dataclass(frozen=True, slots=True)
class Settings:
    bot_token: str
    owner_id: int | None
    welcome_chat_ids: tuple[int, ...] = ()
    nvidia_nim_chat_api_key: str = ""
    nvidia_nim_guardian_api_key: str = ""
    nvidia_nim_model: str = DEFAULT_NIM_MODEL
    nvidia_nim_chat_model: str = DEFAULT_NIM_CHAT_MODEL
    ai_guard_enabled: bool = False
    ai_chat_enabled: bool = False


def load_settings() -> Settings:
    """Load and validate settings without exposing secret values in logs."""
    token = os.getenv("BOT_TOKEN", "").strip()
    if not token:
        raise ConfigurationError("BOT_TOKEN is missing. Set it in the hosting environment.")

    raw_owner_id = os.getenv("OWNER_ID", "").strip()
    owner_id: int | None = None
    if raw_owner_id:
        try:
            owner_id = int(raw_owner_id)
        except ValueError as exc:
            raise ConfigurationError("OWNER_ID must be a numeric Telegram user ID.") from exc
        if owner_id <= 0:
            raise ConfigurationError("OWNER_ID must be a positive Telegram user ID.")

    ai_guard_enabled = os.getenv("AI_GUARD_ENABLED", "false").strip().casefold() in {
        "1", "true", "yes", "on",
    }
    ai_chat_enabled = os.getenv("AI_CHAT_ENABLED", "false").strip().casefold() in {
        "1", "true", "yes", "on",
    }
    legacy_key = os.getenv("NVIDIA_NIM_API_KEY", "").strip()
    chat_api_key = os.getenv("NVIDIA_NIM_CHAT_API_KEY", "").strip() or legacy_key
    guardian_api_key = os.getenv("NVIDIA_NIM_GUARDIAN_API_KEY", "").strip() or legacy_key
    nvidia_nim_model = os.getenv("NVIDIA_NIM_MODEL", DEFAULT_NIM_MODEL).strip()
    nvidia_nim_chat_model = os.getenv(
        "NVIDIA_NIM_CHAT_MODEL", DEFAULT_NIM_CHAT_MODEL
    ).strip()

    return Settings(
        bot_token=token,
        owner_id=owner_id,
        nvidia_nim_chat_api_key=chat_api_key,
        nvidia_nim_guardian_api_key=guardian_api_key,
        nvidia_nim_model=nvidia_nim_model or DEFAULT_NIM_MODEL,
        nvidia_nim_chat_model=nvidia_nim_chat_model or DEFAULT_NIM_CHAT_MODEL,
        ai_guard_enabled=ai_guard_enabled,
        ai_chat_enabled=ai_chat_enabled,
    )
