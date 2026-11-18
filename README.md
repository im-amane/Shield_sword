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

Set `BOT_TOKEN` and `OWNER_ID` in the existing Railway service Variables. Optional public menu links are `MAIN_GROUP_URL` and `OWNER_CONTACT_URL` (HTTPS URLs only). The Add Me button is generated automatically from the bot username. The service starts with `python -m app.main`.

The bot needs these Telegram administrator permissions for the current group features:
- Delete messages: anti-spam cleanup.
- Ban users: temporary restrictions for verification and anti-spam. This permission does not mean the bot automatically bans members.

## Current group protection

- Public welcome messages for new human members.
- Arithmetic captcha verification for every new human member. Members stay restricted until they answer correctly; unanswered challenges expire after 3 minutes and the bot removes the member. Expired challenges are enforced by a persistent worker, including after service restarts.
- Anti-spam: flood detection and temporary 60-second restrictions.
- Automatic raid detection: activates when **500 human members join within 10 minutes**.
- Raid mode lasts **30 minutes** and sends an alert to the group and configured owner. The owner can use `/raidstatus` in a group to inspect it and `/raidoff` to disable it manually.
- During raid mode, all new human members continue to face the existing verification challenge. Existing members are not restricted.

Raid counters and active mode are persisted in SQLite. The database survives process restarts only when its path is on persistent storage. On Railway, attach a Volume mounted at `/data` and set `DATABASE_PATH=/data/aniworld.sqlite3`; without that, redeploys may replace the database.

## Channel media protection

- Channel protection is opt-in and OFF by default, so adding the bot to a channel does not silently remove channel posts.
- Add the bot as a channel administrator with Delete Messages permission.
- In the bot's private chat, a channel administrator can run:
  - `/channelprotect @channel on`
  - `/channelprotect @channel off`
  - `/channelprotect @channel status`
- When enabled, photos, videos, animations, documents, audio, voice notes, video notes and stickers in channel posts are removed, including edited channel posts.
- Important Telegram limitation: channel-post updates do not reliably identify the individual administrator who published a post. Therefore, ON mode removes media from admins too. Enable it only if that is the intended channel policy.
- Channel settings are stored separately from group settings and persist in the Railway database volume.

## Automatic copyright-risk controls

- Every group automatically blocks ordinary members from posting photos, videos, animations/GIFs, documents, audio, voice notes, video notes and stickers. No setup command is required.
- Group admins can still publish approved media; text discussion remains available.
- The filter also checks edited media messages and records removal metadata in the security audit log.
- This is a group-level upload policy, not a copyright ownership detector or legal guarantee. It does not yet moderate channel posts. Channel protection requires a separate channel-admin integration and Telegram's Restrict Saving Content setting should also be enabled manually where appropriate.
- Use licensed/official anime sources and respond to valid rights-holder notices.

## Security

- All bot-sent messages/documents use Telegram's protected-content flag by default to discourage forwarding and saving.
- This does not prevent screenshots, screen recording, copying text manually, or protect user-posted content. Enable Telegram channel/group Restrict Saving Content in chat settings for stronger chat-wide controls.
- Owner-only `/panel` opens the private control center with Overview, Security Intelligence, Groups, Member Activity, Audit Log, Database Health, Secure Configuration, Automation Monitor, Command Index, and one-tap encrypted backup.
- The Configuration panel reports whether required secrets/settings are present and displays only a short SHA-256 fingerprint for the backup key. It never displays bot tokens, encryption keys, or other secret values in Telegram.
- The dashboard records groups the bot observes, new-member join timestamps, public Telegram usernames/display names and user IDs, raid alerts, anti-spam, anti-link, bad-word and media-policy incidents.
- An early-warning alert is sent to the owner when 25 human accounts join within 60 seconds. This is an alert only; it does not automatically ban or restrict members. The existing 500-joins/10-minute threshold activates Raid Mode.
- Join history is capped at the newest 5,000 records and security incidents at 3,000. Audit events are capped at 5,000. Stored intelligence is metadata only: no message bodies, phone numbers, IP addresses, device details or bot tokens are collected.
- Use `/audit`, `/dbstatus` and `/backup` in the bot's private chat. The dashboard and backup are private-only so database files and incident details are never posted into a group.
- Automatic verified SQLite backups are sent to the configured owner once every 7 days. The last successful delivery time is stored in the persistent database, so service restarts do not trigger duplicate backups. The first backup is sent shortly after the first-ever startup. Keep a separate copy outside Telegram/Railway for disaster recovery.
- Telegram bots cannot see a member's IP address, device fingerprint, phone number or real-world identity unless the user separately shares that information. The dashboard only shows information Telegram makes available to the bot.
- Audit and incident records contain moderation/security metadata only; never store bot tokens or private message contents.


Never commit `.env`, paste bot tokens into chats, or print secrets in logs. If a token is exposed, revoke it through @BotFather and create a new one.


## Global inline UI
- Bot replies in groups and private chats include a `✖️ Close` inline button. Existing inline actions are preserved. Tapping Close deletes that bot message for everyone in the chat.


## Daily owner security reports
- A daily security summary is sent to the configured owner in private chat.
- It includes monitored groups, new member joins, recent security incidents, raid detections, anti-spam actions and active raid modes.
- Successful delivery time is persisted in SQLite, so a service restart does not cause duplicate reports. The first report is sent shortly after the first-ever startup; failed deliveries retry after one hour.


## Encrypted database backups

- Manual `/backup`, the Owner Panel's one-tap backup, and automatic weekly backups are encrypted with AES-256-GCM before they leave the service.
- Configure `BACKUP_ENCRYPTION_KEY` as a Railway secret/environment variable. It must be URL-safe base64 encoding of exactly 32 random bytes. The bot fails closed and will not send plaintext backups if the key is missing or invalid.
- Keep an offline, access-controlled copy of this key separately from Telegram and Railway backups. Losing the key makes encrypted backups unrecoverable. Never commit it to GitHub or send it in chat.
- Encrypted files use the `.sqlite3.awb` extension and the versioned `AWB1` envelope. Restore tooling must authenticate/decrypt with the same key before validating the resulting SQLite database.
- Existing backups created before this change remain unencrypted. Protect or securely dispose of those older files according to your retention needs; they are not retroactively encrypted.
