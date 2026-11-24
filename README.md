# Ani World 剣 Management Bot

A Telegram group security and management bot. It is built one feature at a time, with automated tests and deployment verification.

## Stack

- Python 3.11+
- aiogram 3
- SQLite on Railway persistent storage
- NVIDIA NIM safety classifier (optional AI Guard)
- Telegram long polling

## Run locally

1. Create a bot with [@BotFather](https://t.me/BotFather).
2. Set `BOT_TOKEN` and `OWNER_ID` in your environment.
3. Install dependencies and start:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export BOT_TOKEN="your-token"
export OWNER_ID="your-telegram-user-id"
python -m app.main
```

## Railway configuration

Required:
- `BOT_TOKEN`
- `OWNER_ID`

AI Guard (optional; runs only when explicitly enabled and the guardian key is configured):
- `AI_GUARD_ENABLED=true`
- `NVIDIA_NIM_GUARDIAN_API_KEY`
- Optional `NVIDIA_NIM_MODEL`; defaults to `nvidia/llama-3.1-nemotron-safety-guard-8b-v3`

Other optional settings:
- `MAIN_GROUP_URL`
- `OWNER_CONTACT_URL`
- `DATABASE_PATH=/data/aniworld.sqlite3`
- `BACKUP_ENCRYPTION_KEY` (required for encrypted backup delivery)

There is no conversational AI Chat feature or chat-model API configuration. AI Guard is a moderation classifier only.

## Group protection

- New human members receive an arithmetic CAPTCHA and remain restricted until they answer correctly.
- Unanswered challenges expire after 3 minutes; a persistent worker enforces expiry after restarts.
- Anti-spam detects flood behavior and applies temporary 60-second restrictions.
- Raid mode activates at 500 human joins within 10 minutes, lasts 30 minutes, and alerts the group and owner. The owner can inspect with `/raidstatus` and disable with `/raidoff`.
- An early-warning owner alert is sent when 25 human accounts join within 60 seconds. This alert does not itself ban or restrict members.
- AI Guard checks group messages and channel posts that contain text or captions for high-risk safety categories. In groups, it exempts the owner, admins, bots and commands. Channel posts are moderated at the post level without attempting to identify an individual poster. Provider or group member-lookup failures do not trigger AI deletion.
- Existing anti-link, bad-word and anti-spam filters remain active.

## Media policy and copyright limitations

- Ordinary group photos, videos, GIFs, documents, audio, voice notes, video notes and stickers are allowed. Group media is not blanket-deleted.
- Text and captions remain subject to the relevant group safety filters.
- Channel posts containing text or captions are checked by AI Guard when it is enabled. Posts with no text/caption are not scanned or deleted by this feature.
- No blanket channel-media deletion or `/channelprotect` command is implemented. Ordinary media is not deleted merely because of its file type.
- The bot does not verify copyright ownership or detect visual copyright infringement. No copyright-related deletion is performed on ordinary group media. Handle rights-holder complaints through review and use licensed/official sources.

## Moderation and management

- Admin moderation commands include mute, unmute, ban, kick, unban and purge.
- Warning controls include `/unwarn` and `/resetwarn`; owner/admin access is enforced by the relevant handlers.
- Owner-only `/panel` opens the private control center with Overview, Security Intelligence, Groups, Member Activity, Audit Log, Database Health, Secure Configuration, Automation Monitor, Command Index and encrypted backup.
- Use `/audit`, `/dbstatus`, `/backup` and `/aitest` in the bot's private chat as appropriate.
- The daily owner security report and weekly automatic backup use persisted delivery timestamps to avoid duplicate sends after restarts.

## Storage, audit and backups

- Mount a Railway Volume at `/data` and set `DATABASE_PATH=/data/aniworld.sqlite3` so SQLite data survives redeploys.
- The dashboard records group observations, join timestamps, usernames/display names and user IDs, raid alerts, and moderation/security incident metadata.
- Stored intelligence does not include message bodies, phone numbers, IP addresses, device details or bot tokens.
- Join history is capped at 5,000 records, security incidents at 3,000 and audit events at 5,000.
- Manual and automatic backups are encrypted with AES-256-GCM before delivery. `BACKUP_ENCRYPTION_KEY` must be URL-safe base64 encoding of exactly 32 random bytes. The bot fails closed rather than sending plaintext if the key is missing or invalid.
- Keep an offline, access-controlled copy of the encryption key. Losing it makes encrypted backups unrecoverable. Older backups created before encryption are not retroactively protected.

## Telegram permissions

The bot needs only the administrator permissions required for the enabled features:
- Delete Messages: removal of content explicitly classified unsafe by moderation.
- Restrict Members: CAPTCHA and temporary anti-spam/AI-warning mutes.
- Ban Users: member removal and verification expiry.

Telegram bots cannot see a member's IP address, device fingerprint, phone number or real-world identity unless the user separately shares that information.

Never commit `.env`, paste bot tokens into chats, or print secrets in logs. If a token is exposed, revoke it through @BotFather and create a new one.
