# Ani World 剣 Management Bot

The first milestone is the **Bot Core**: validated configuration, Telegram connection, structured logging, and a working `/start` health check. Community-management modules will be added one at a time and tested before moving on.

## Stack

- Python 3.11+
- aiogram 3
- Railway environment variables
- Telegram long polling

## Run locally

1. Create a bot with [@BotFather](https://t.me/BotFather).
2. Copy `.env.example` to `.env` and set `BOT_TOKEN`.
3. Install dependencies and start the bot:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Export the environment variable before running:

```bash
export BOT_TOKEN="your-token"
python -m app.main
```

On Windows PowerShell:

```powershell
$env:BOT_TOKEN="your-token"
python -m app.main
```

Open the bot in Telegram and send `/start`. It should reply that the core connection test succeeded. Set `OWNER_ID` to your numeric Telegram user ID, then use `/owner` to verify authorization and `/panel` to open the owner dashboard.

## Railway deployment

1. Create a Railway service from this GitHub repository.
2. Add `BOT_TOKEN` and `OWNER_ID` in the service's Variables. `OWNER_ID` is required for owner-only commands and the dashboard.
3. Railway uses `python -m app.main` as the start command from `railway.json`.
4. Deploy, inspect the logs for the Telegram connection message, then send `/start`.

**Security:** Never commit `.env`, paste bot tokens into chats, or print secrets in logs. If a token is exposed, revoke it through @BotFather and create a new one.

## Current status

- [x] Project skeleton
- [x] Environment configuration validation
- [x] Telegram bot startup and connection check
- [x] `/start` command
- [x] Owner authentication command and fail-closed authorization helper
- [x] Owner dashboard with refresh and close controls
- [ ] Automated test suite verified in CI
- [ ] Live owner dashboard test

No moderation or group-management permissions are needed for this first milestone. Add only the permissions required by each later module.
