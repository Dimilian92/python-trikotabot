# Telegram Scheduled Notifier Bot

Python Telegram bot that sends scheduled notifications to any chat where notifications are enabled.

## Features
- Configure recipients (`@username`), message, weekdays, and times in code.
- Enable notifications in a chat with `/enable_notifications`.
- Disable notifications in a chat with `/disable_notifications`.
- Show configured rules with `/rules`.
- Send a test message immediately with `/sendnow <rule_name>`.
- Includes a daily `cat_of_the_day` nomination at `10:00` with a random image from the query `funny cat mem`.

## 1) Create your bot token
1. Open Telegram and chat with `@BotFather`.
2. Run `/newbot` and copy the token.

## 2) Setup
```bash
cd telegram_notifier_bot
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
```

Create `.env` from `.env.example` and set:
```env
TELEGRAM_BOT_TOKEN=123456:ABC...
```

## 3) Configure notification rules
Edit `notification_config.py`.

Current defaults include your example:
- `@lyda` Monday-Friday at `09:00` -> `Please check in, my love`
- `@lyda` Monday-Friday at `18:00` -> `Please check out`
- `@vio` Monday-Friday at `11:00` -> `Please drink colagen`
- `@vio` Monday-Friday at `18:00` -> `time to drop all and walk`
- `cat_of_the_day` daily at `10:00` -> random nominee (`@vio` or `@lyda`) and random cat image

Timezone is controlled by:
```python
BOT_TIMEZONE = "Europe/Berlin"
```

## 4) Run the bot
```bash
python bot.py
```

## 5) Use in Telegram
1. Add bot to your group or chat.
2. In that chat run `/enable_notifications`.
3. Optional: run `/rules` or `/sendnow lyda_check_in` to verify.

## Commands
- `/start`
- `/enable_notifications`
- `/disable_notifications`
- `/notifications_status`
- `/rules`
- `/chat_id`
- `/sendnow <rule_name>`
