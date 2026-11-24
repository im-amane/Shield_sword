"""Bounded NVIDIA NIM Chat Completions client and diagnostics."""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

NIM_CHAT_COMPLETIONS_URL = "https://integrate.api.nvidia.com/v1/chat/completions"


@dataclass(frozen=True, slots=True)
class NimResponse:
    text: str | None
    latency_ms: int
    error: str | None = None
    http_status: int | None = None


def request_nim_completion(
    api_key: str,
    model: str,
    messages: list[dict[str, str]],
    *,
    timeout: float = 8.0,
    max_tokens: int = 160,
) -> NimResponse:
    """Call one NIM model; never return/log credentials or provider error bodies."""
    if not api_key.strip() or not model.strip():
        return NimResponse(None, 0, "missing_configuration")
    body = json.dumps({
        "model": model,
        "messages": messages,
        "temperature": 0,
        "max_tokens": max(1, min(int(max_tokens), 512)),
        "stream": False,
    }).encode("utf-8")
    request = urllib.request.Request(
        NIM_CHAT_COMPLETIONS_URL,
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    started = time.monotonic()
    try:
        with urllib.request.urlopen(request, timeout=max(1.0, min(timeout, 8.0))) as response:
            status = response.status
            payload = json.loads(response.read(64_000).decode("utf-8"))
        choices = payload.get("choices")
        if not isinstance(choices, list) or not choices:
            return NimResponse(None, int((time.monotonic() - started) * 1000), "invalid_response", status)
        message = choices[0].get("message", {}) if isinstance(choices[0], dict) else {}
        content: Any = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, str) or not content.strip():
            return NimResponse(None, int((time.monotonic() - started) * 1000), "empty_response", status)
        return NimResponse(content.strip()[:2000], int((time.monotonic() - started) * 1000), None, status)
    except urllib.error.HTTPError as exc:
        return NimResponse(None, int((time.monotonic() - started) * 1000), f"http_{exc.code}", exc.code)
    except (urllib.error.URLError, TimeoutError, OSError):
        return NimResponse(None, int((time.monotonic() - started) * 1000), "network_or_timeout")
    except (ValueError, KeyError, TypeError, UnicodeDecodeError):
        return NimResponse(None, int((time.monotonic() - started) * 1000), "invalid_response")
