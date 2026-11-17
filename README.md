# Ani World 剣 Management Bot

The bot is built one feature at a time, with automated tests and live verification before moving to the next module.

## Stack

- Python 3.11+
- aiogram 3
- Railway environment variables
- Telegram long polling

## Run locally

1. Create a bot with [@BotFather](https://t.me/BotFather).
2. Set `BOT_TOKEN` in your environment.
3. Install dependencies and start:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export BOT_TOKEN="your-token"
export OWNER_ID="your-telegram-user-id"
python -m app.main
```

On Windows PowerShell:

```powershell
$env:BOT_TOKEN="your-token"
$env:OWNER_ID="your-telegram-user-id"
python -m app.main
```

## Railway deployment

Set `BOT_TOKEN` and `OWNER_ID` in the existing Railway service Variables. The service starts with `python -m app.main`.

The bot needs these Telegram administrator permissions for the current group features:
- Delete messages: anti-spam cleanup.
- Ban users: temporary restrictions for verification and anti-spam. This permission does not mean the bot automatically bans members.

## Current group protection

- Public welcome messages for new human members.
- Arithmetic captcha verification for every new human member.
- Anti-spam: flood detection and temporary 60-second restrictions.
- Automatic raid detection: activates when **500 human members join within 10 minutes**.
- Raid mode lasts **30 minutes** and sends an alert to the group and configured owner. The owner can use `/raidstatus` in a group to inspect it and `/raidoff` to disable it manually.
- During raid mode, all new human members continue to face the existing verification challenge. Existing members are not restricted.

Raid counters and active mode are persisted in SQLite. The database survives process restarts only when its path is on persistent storage. On Railway, attach a Volume mounted at `/data` and set `DATABASE_PATH=/data/aniworld.sqlite3`; without that, redeploys may replace the database.

## Automatic copyright-risk controls

- Every group automatically blocks ordinary members from posting photos, videos, animations/GIFs, documents, audio, voice notes, video notes and stickers. No setup command is required.
- Group admins can still publish approved media; text discussion remains available.
- The filter also checks edited media messages and records removal metadata in the security audit log.
- This is a group-level upload policy, not a copyright ownership detector or legal guarantee. It does not yet moderate channel posts. Channel protection requires a separate channel-admin integration and Telegram's Restrict Saving Content setting should also be enabled manually where appropriate.
- Use licensed/official anime sources and respond to valid rights-holder notices.

## Security

- All bot-sent messages/documents use Telegram's protected-content flag by default to discourage forwarding and saving.
- This does not prevent screenshots, screen recording, copying text manually, or protect user-posted content. Enable Telegram channel/group Restrict Saving Content in chat settings for stronger chat-wide controls.
- Owner-only `/panel` opens the private control center with Overview, Security Intelligence, Groups, Member Activity, Audit Log, Database Health, and a one-tap manual backup.
- The dashboard records groups the bot observes, new-member join timestamps, public Telegram usernames/display names and user IDs, raid alerts, anti-spam, anti-link, bad-word and media-policy incidents.
- An early-warning alert is sent to the owner when 25 human accounts join within 60 seconds. This is an alert only; it does not automatically ban or restrict members. The existing 500-joins/10-minute threshold activates Raid Mode.
- Join history is capped at the newest 5,000 records and security incidents at 3,000. Audit events are capped at 5,000. Stored intelligence is metadata only: no message bodies, phone numbers, IP addresses, device details or bot tokens are collected.
- Use `/audit`, `/dbstatus` and `/backup` in the bot's private chat. The dashboard and backup are private-only so database files and incident details are never posted into a group.
- Automatic verified SQLite backups are sent to the configured owner once every 7 days. The last successful delivery time is stored in the persistent database, so service restarts do not trigger duplicate backups. The first backup is sent shortly after the first-ever startup. Keep a separate copy outside Telegram/Railway for disaster recovery.
- Telegram bots cannot see a member's IP address, device fingerprint, phone number or real-world identity unless the user separately shares that information. The dashboard only shows information Telegram makes available to the bot.
- Audit and incident records contain moderation/security metadata only; never store bot tokens or private message contents.


Never commit `.env`, paste bot tokens into chats, or print secrets in logs. If a token is exposed, revoke it through @BotFather and create a new one.
