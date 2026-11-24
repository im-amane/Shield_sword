# NVIDIA NIM AI Guard

Guardian can optionally call NVIDIA's hosted NIM Chat Completions API to classify group text for targeted harassment, credible threats, hate, doxxing, scams/fraud, malware, and actionable serious wrongdoing.

## Environment configuration

Set these only in Railway Variables (never commit the API key):

- `NVIDIA_NIM_API_KEY`: NVIDIA API key.
- `NVIDIA_NIM_MODEL`: defaults to `nvidia/llama-3.1-nemotron-safety-guard-8b-v3`.
- `AI_GUARD_ENABLED`: defaults to `false`; set to `true` only after the API key is configured.

The feature is disabled by default. If it is enabled without a key, Guardian logs a warning and continues with existing protection. AI classification failures, timeouts, malformed output, or Telegram member-verification failures do not stop polling and do not trigger moderation.

## Safeguards

- Only text/captions from non-admin group members are sent; messages are capped at 1,600 characters.
- Commands, bot messages, the configured owner, group creators, and group administrators are excluded.
- API calls are bounded to one scan per user every 8 seconds, four per group per second, and five per bot per second.
- The model output must parse as JSON with an explicit `User Safety` value of `unsafe`; malformed/ambiguous output is ignored.
- A flagged message is deleted before a warning is recorded. Existing warning escalation applies.
- Raw message text and API keys are not written to Guardian logs or the database.
- Existing deterministic filters remain active; the AI layer supplements them and is not a replacement.

## Privacy and limitations

When enabled, message text is transmitted to NVIDIA's hosted API for classification. Do not enable this feature unless the community's privacy notice and applicable data-handling requirements permit that processing. NVIDIA's hosted API trial terms and model license apply. AI classification can make mistakes; test with representative Hindi and English community messages before relying on automatic deletion. The request limiter intentionally means not every message is sent for AI scanning.

This is an AI content-safety classifier, not a guaranteed spam/phishing detector or a substitute for human moderation.
