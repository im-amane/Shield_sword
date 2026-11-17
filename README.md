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
- Raid mode lasts **30 minutes** and sends an alert to the group and configured owner.
- During raid mode, all new human members continue to face the existing verification challenge. Existing members are not restricted.

Raid counters and active mode are currently held in memory, so a service restart resets the detection window and active raid state. Persistent storage is a planned hardening step before relying on this for large-scale incident response.

## Security

Never commit `.env`, paste bot tokens into chats, or print secrets in logs. If a token is exposed, revoke it through @BotFather and create a new one.
