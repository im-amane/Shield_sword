# NVIDIA NIM AI integration

## Models
- Chat: `nvidia/nemotron-3.5-bolt-e4b` (NVIDIA currently lists a Free Endpoint).
- Safety: `nvidia/llama-3.1-nemotron-safety-guard-8b-v3` (NVIDIA currently lists a Free Endpoint).
- Both use the OpenAI-compatible NVIDIA NIM Chat Completions endpoint and the same `NVIDIA_NIM_API_KEY`.

## Railway variables
- `NVIDIA_NIM_API_KEY`: secret key; never commit or print it.
- `NVIDIA_NIM_CHAT_MODEL`: optional; defaults to the chat model above.
- `NVIDIA_NIM_MODEL`: optional; defaults to the safety model above.
- `AI_GUARD_ENABLED`: defaults to false. Controls automatic moderation only.
- `AI_CHAT_ENABLED`: reserved for the conversational group router; defaults to false. Diagnostics do not enable either feature.

## Owner diagnostics
Use `/aitest` in the bot's private chat. It sends fixed, harmless test prompts to both configured model IDs, reports latency and sanitized error categories, and shows a short chat response. It does not send group messages, change feature flags, or log the API key. The command is private-chat and configured-owner only.

## Safety and rollout
- API requests have an 8-second timeout and bounded response size.
- Provider response bodies and credentials are not exposed in diagnostic messages.
- A successful model response proves endpoint access only; it does not certify moderation quality.
- Automatic AI moderation remains opt-in. AI Chat remains disabled until its interaction policy, cooldowns, context handling and group-level tests are implemented.
- NVIDIA marks the listed endpoints as Free Endpoint in its catalog; quotas, availability and applicable trial terms can change. Verify terms before production use in a live community.
- When automatic classification is enabled, eligible group text is transmitted to NVIDIA for processing. Publish an appropriate privacy notice and assess applicable data-handling requirements first.
