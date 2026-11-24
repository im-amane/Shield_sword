"""Independent API-key routing for Guardian's chat and safety AI engines."""
from __future__ import annotations

from dataclasses import dataclass

from app.ai_chat import NimChatClient
from app.ai_guard import NimSafetyClient


@dataclass(slots=True)
class GuardianAIEngine:
    """Keep chat generation and safety classification on separate credentials."""

    chat: NimChatClient
    guardian: NimSafetyClient

    @classmethod
    def create(
        cls,
        chat_api_key: str,
        guardian_api_key: str,
        chat_model: str,
        guardian_model: str,
    ) -> "GuardianAIEngine":
        if not chat_api_key.strip():
            raise ValueError("Chat API key is missing.")
        if not guardian_api_key.strip():
            raise ValueError("Guardian API key is missing.")
        return cls(
            chat=NimChatClient(chat_api_key, chat_model),
            guardian=NimSafetyClient(guardian_api_key, guardian_model, timeout=20.0),
        )
