# NVIDIA NIM AI integration

## Independent AI engines
- Chat engine: `nvidia/nemotron-3.5-bolt-e4b`, authenticated with `NVIDIA_NIM_CHAT_API_KEY`.
- Guardian safety engine: `nvidia/llama-3.1-nemotron-safety-guard-8b-v3`, authenticated with `NVIDIA_NIM_GUARDIAN_API_KEY`.
- Both use NVIDIA's OpenAI-compatible Chat Completions endpoint, but credentials and client instances are separate.

## Railway variables
- `NVIDIA_NIM_CHAT_API_KEY`: secret used only for chat generation.
- `NVIDIA_NIM_GUARDIAN_API_KEY`: separate secret used for input/output safety classification and optional automatic AI Guard.
- `NVIDIA_NIM_API_KEY`: temporary legacy fallback when a role-specific key is not supplied. Configure both dedicated keys, then remove the legacy variable.
- `NVIDIA_NIM_CHAT_MODEL`: optional chat model override.
- `NVIDIA_NIM_MODEL`: optional Guardian safety model override.
- `AI_CHAT_ENABLED`: enables mention/reply-driven group conversations.
- `AI_GUARD_ENABLED`: controls separate automatic moderation and remains false unless explicitly enabled.

## Owner diagnostics
Use `/aitest` in the bot's private chat. It tests chat and Guardian engines independently with their respective keys. It reports sanitized status and latency and does not change feature flags or log credentials.

## Chat behaviour and safeguards
- Guardian responds in groups when mentioned as `Guardian` / `@Break_mebot`, or when a member replies to Guardian.
- Per-user cooldown is 12 seconds, per-group 4 seconds, and bot-wide 1 second.
- Incoming text and generated output are independently screened by the Guardian engine. If a check fails, is uncertain, or times out, no AI reply is posted.
- Only a bounded excerpt of the triggering message is sent to NVIDIA. No conversation history or database profile is transmitted.
- Chat replies are escaped before Telegram delivery.

## Reliability and security
- Guardian safety requests have a bounded 20-second timeout and one bounded retry for transient HTTP 502/503/504 responses.
- Provider response bodies and credentials are never logged.
- Standalone AI Guard remains independent from the safety checks required for AI Chat.
- A successful endpoint test proves connectivity only; it does not certify moderation quality. Provider quotas and availability can change.
- When enabled, eligible group text is transmitted to NVIDIA for processing. Publish an appropriate privacy notice and assess applicable data-handling requirements.
