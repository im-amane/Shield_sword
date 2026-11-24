# NVIDIA NIM AI integration

## Models
- Chat: `nvidia/nemotron-3.5-bolt-e4b` (NVIDIA currently lists a Free Endpoint).
- Safety: `nvidia/llama-3.1-nemotron-safety-guard-8b-v3` (NVIDIA currently lists a Free Endpoint).
- Both use the OpenAI-compatible NVIDIA NIM Chat Completions endpoint and the same `NVIDIA_NIM_API_KEY`.

## Railway variables
- `NVIDIA_NIM_API_KEY`: secret key; never commit or print it.
- `NVIDIA_NIM_CHAT_MODEL`: optional; defaults to the chat model above.
- `NVIDIA_NIM_MODEL`: optional; defaults to the safety model above.
- `AI_GUARD_ENABLED`: defaults to false. Controls automatic moderation.
- `AI_CHAT_ENABLED`: defaults to false. Enables mention/reply-driven group conversations.

## Owner diagnostics
Use `/aitest` in the bot's private chat. It sends fixed, harmless test prompts to both configured model IDs, reports latency and sanitized error categories, and shows a short chat response. It does not send group messages, change feature flags, or log the API key.

## Chat behaviour and safeguards
- Guardian responds only when a member mentions `Guardian` / `@Break_mebot`, or replies to Guardian. It does not reply to every group message or initiate unsolicited group messages.
- Per-user 45-second, per-group 8-second and bot-wide 2-second cooldowns bound calls.
- Incoming member text is screened before generation; generated output is screened again. If either safety check fails, is uncertain, or times out, no reply is posted.
- Only a bounded excerpt of the triggering message is sent to NVIDIA. No conversation history or database profile is transmitted.
- Chat replies are escaped as plain text before Telegram delivery.

## Safety and rollout
- API requests have an 8-second maximum timeout; safety checks use a 4-second timeout.
- Provider response bodies and credentials are not exposed in diagnostic messages or logs.
- A successful model response proves endpoint access only; it does not certify moderation quality.
- Automatic AI moderation and AI Chat remain opt-in. Verify both models with `/aitest` before enabling the corresponding flag.
- NVIDIA marks the listed endpoints as Free Endpoint in its catalog; quotas, availability and applicable trial terms can change. Verify terms before production use in a live community.
- When enabled, eligible group text is transmitted to NVIDIA for processing. Publish an appropriate privacy notice and assess applicable data-handling requirements first.
