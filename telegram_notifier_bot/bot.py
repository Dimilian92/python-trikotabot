from __future__ import annotations

import asyncio
import json
import logging
import os
import random
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from telegram import Update
from telegram.error import Forbidden, TelegramError
from telegram.ext import Application, CommandHandler, ContextTypes
from zoneinfo import ZoneInfo

from notification_config import BOT_TIMEZONE, NOTIFICATION_RULES, NotificationRule

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None


logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

REGISTERED_CHATS_FILE = Path(__file__).with_name("registered_chats.json")
REGISTERED_CHATS_LOCK = asyncio.Lock()
VALID_DAYS = {"mon", "tue", "wed", "thu", "fri", "sat", "sun"}
RULES_BY_NAME = {rule.name: rule for rule in NOTIFICATION_RULES}


def _read_registered_chats() -> set[int]:
    if not REGISTERED_CHATS_FILE.exists():
        return set()

    try:
        raw = json.loads(REGISTERED_CHATS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        logger.exception("Cannot read %s.", REGISTERED_CHATS_FILE)
        return set()

    if not isinstance(raw, list):
        logger.warning("Expected a JSON list in %s.", REGISTERED_CHATS_FILE)
        return set()

    chat_ids: set[int] = set()
    for item in raw:
        try:
            chat_ids.add(int(item))
        except (TypeError, ValueError):
            logger.warning("Skipping invalid chat id %r", item)
    return chat_ids


def _write_registered_chats(chat_ids: set[int]) -> None:
    ordered = sorted(chat_ids)
    REGISTERED_CHATS_FILE.write_text(json.dumps(ordered, indent=2), encoding="utf-8")


async def _get_registered_chats() -> set[int]:
    async with REGISTERED_CHATS_LOCK:
        return _read_registered_chats()


async def _register_chat(chat_id: int) -> tuple[bool, int]:
    async with REGISTERED_CHATS_LOCK:
        chat_ids = _read_registered_chats()
        if chat_id in chat_ids:
            return False, len(chat_ids)

        chat_ids.add(chat_id)
        _write_registered_chats(chat_ids)
        return True, len(chat_ids)


async def _unregister_chat(chat_id: int) -> tuple[bool, int]:
    async with REGISTERED_CHATS_LOCK:
        chat_ids = _read_registered_chats()
        if chat_id not in chat_ids:
            return False, len(chat_ids)

        chat_ids.remove(chat_id)
        _write_registered_chats(chat_ids)
        return True, len(chat_ids)


async def _remove_stale_chats(stale_chat_ids: set[int]) -> None:
    if not stale_chat_ids:
        return

    async with REGISTERED_CHATS_LOCK:
        chat_ids = _read_registered_chats()
        updated = chat_ids - stale_chat_ids
        if updated != chat_ids:
            _write_registered_chats(updated)


def _format_rule(rule: NotificationRule) -> str:
    mentions = " ".join(rule.mentions) if rule.mentions else "(no mentions)"
    days = ",".join(rule.days)
    times = ",".join(rule.times)
    variants = len(rule.messages)
    preview = rule.messages[0]
    return f"{rule.name}: {mentions} | {days} | {times} | {variants} variants | e.g. {preview}"


def _format_notification_text(rule: NotificationRule) -> str:
    mentions = " ".join(rule.mentions).strip()
    message = random.choice(rule.messages)
    if mentions:
        return f"{mentions}\n{message}"
    return message


async def _send_rule_to_chat(application: Application, chat_id: int, rule: NotificationRule) -> None:
    await application.bot.send_message(
        chat_id=chat_id,
        text=_format_notification_text(rule),
    )


def _parse_clock(clock: str) -> tuple[int, int]:
    try:
        hour_str, minute_str = clock.split(":", maxsplit=1)
        hour = int(hour_str)
        minute = int(minute_str)
    except ValueError as exc:
        raise ValueError(f"Invalid time format: {clock}. Use HH:MM.") from exc

    if hour not in range(24) or minute not in range(60):
        raise ValueError(f"Invalid time: {clock}.")
    return hour, minute


def _validate_rule(rule: NotificationRule) -> None:
    if not rule.name:
        raise ValueError("Every rule must have a name.")
    if not rule.messages:
        raise ValueError(f"Rule {rule.name} has no messages.")
    if len(rule.messages) < 7:
        raise ValueError(f"Rule {rule.name} must define at least 7 message variants.")
    if not rule.days:
        raise ValueError(f"Rule {rule.name} has no days.")
    if not rule.times:
        raise ValueError(f"Rule {rule.name} has no times.")

    for message in rule.messages:
        if not message.strip():
            raise ValueError(f"Rule {rule.name} includes an empty message variant.")
    for day in rule.days:
        if day not in VALID_DAYS:
            raise ValueError(
                f"Rule {rule.name} has invalid day '{day}'. "
                f"Use one of {sorted(VALID_DAYS)}."
            )
    for clock in rule.times:
        _parse_clock(clock)


async def _send_rule_to_chats(application: Application, rule: NotificationRule) -> None:
    chat_ids = await _get_registered_chats()
    if not chat_ids:
        logger.info("No chats registered. Skipping rule %s", rule.name)
        return

    stale_chat_ids: set[int] = set()

    for chat_id in chat_ids:
        try:
            await _send_rule_to_chat(application=application, chat_id=chat_id, rule=rule)
            logger.info("Sent rule '%s' to chat %s", rule.name, chat_id)
        except Forbidden:
            logger.warning("Bot was removed from chat %s. Removing registration.", chat_id)
            stale_chat_ids.add(chat_id)
        except TelegramError:
            logger.exception("Telegram API error when sending rule %s to chat %s", rule.name, chat_id)

    if stale_chat_ids:
        try:
            await _remove_stale_chats(stale_chat_ids)
        except OSError:
            logger.exception("Cannot update registered chats after stale removals: %s", stale_chat_ids)


def _schedule_rules(application: Application, scheduler: AsyncIOScheduler) -> None:
    tz = ZoneInfo(BOT_TIMEZONE)
    for rule in NOTIFICATION_RULES:
        _validate_rule(rule)
        for day in rule.days:
            for clock in rule.times:
                hour, minute = _parse_clock(clock)
                job_id = f"{rule.name}:{day}:{clock}"
                scheduler.add_job(
                    _send_rule_to_chats,
                    trigger=CronTrigger(
                        day_of_week=day,
                        hour=hour,
                        minute=minute,
                        timezone=tz,
                    ),
                    kwargs={"application": application, "rule": rule},
                    id=job_id,
                    replace_existing=True,
                    coalesce=True,
                    misfire_grace_time=300,
                )
                logger.info("Scheduled %s on %s at %s (%s)", rule.name, day, clock, BOT_TIMEZONE)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_message or not update.effective_chat:
        return

    help_text = (
        "This bot sends scheduled reminders.\n"
        "Commands:\n"
        "/enable_notifications - enable notifications in this chat\n"
        "/disable_notifications - disable notifications in this chat\n"
        "/notifications_status - check if this chat is registered\n"
        "/rules - show active rules from code\n"
        "/chat_id - show this chat id\n"
        "/sendnow <rule_name> - send one rule right now to this chat"
    )
    await update.effective_message.reply_text(help_text)


async def enable_notifications_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if not update.effective_message or not update.effective_chat:
        return

    chat_id = update.effective_chat.id
    try:
        added, total = await _register_chat(chat_id)
    except OSError:
        logger.exception("Cannot save notifications enable for chat %s", chat_id)
        await update.effective_message.reply_text("Cannot save chat registration right now. Please try again.")
        return

    if not added:
        await update.effective_message.reply_text(
            f"Notifications are already enabled in this chat.\nChat ID: {chat_id}\nRegistered chats: {total}"
        )
        return

    await update.effective_message.reply_text(
        f"Notifications are enabled for this chat.\nChat ID: {chat_id}\nRegistered chats: {total}"
    )


async def disable_notifications_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if not update.effective_message or not update.effective_chat:
        return

    chat_id = update.effective_chat.id
    try:
        removed, total = await _unregister_chat(chat_id)
    except OSError:
        logger.exception("Cannot save notifications disable for chat %s", chat_id)
        await update.effective_message.reply_text(
            "Cannot update chat registration right now. Please try again."
        )
        return

    if not removed:
        await update.effective_message.reply_text(
            f"Notifications are not enabled in this chat.\nChat ID: {chat_id}\nRegistered chats: {total}"
        )
        return

    await update.effective_message.reply_text(
        f"Notifications are disabled in this chat.\nChat ID: {chat_id}\nRegistered chats: {total}"
    )


async def rules_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_message:
        return

    lines = ["Rules loaded from notification_config.py:"]
    lines.extend(f"- {_format_rule(rule)}" for rule in NOTIFICATION_RULES)
    await update.effective_message.reply_text("\n".join(lines))


async def chat_id_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_message or not update.effective_chat:
        return
    await update.effective_message.reply_text(f"Chat ID: {update.effective_chat.id}")


async def notifications_status_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if not update.effective_message or not update.effective_chat:
        return

    chat_id = update.effective_chat.id
    chat_ids = await _get_registered_chats()
    status = "enabled" if chat_id in chat_ids else "disabled"
    await update.effective_message.reply_text(
        f"Chat ID: {chat_id}\nNotifications: {status}\nRegistered chats: {len(chat_ids)}"
    )


async def sendnow_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_message or not update.effective_chat:
        return

    if not context.args:
        await update.effective_message.reply_text("Usage: /sendnow <rule_name>")
        return

    rule_name = context.args[0]
    rule = RULES_BY_NAME.get(rule_name)
    if rule is None:
        known = ", ".join(sorted(RULES_BY_NAME))
        await update.effective_message.reply_text(
            f"Unknown rule '{rule_name}'. Available: {known}"
        )
        return

    try:
        await _send_rule_to_chat(
            application=context.application,
            chat_id=update.effective_chat.id,
            rule=rule,
        )
    except TelegramError:
        logger.exception("Failed manual send for rule %s", rule.name)
        await update.effective_message.reply_text("Cannot send message right now.")
        return

    await update.effective_message.reply_text(f"Rule '{rule.name}' sent.")


async def _post_init(application: Application) -> None:
    scheduler = AsyncIOScheduler(timezone=ZoneInfo(BOT_TIMEZONE))
    _schedule_rules(application, scheduler)
    scheduler.start()
    application.bot_data["scheduler"] = scheduler
    logger.info("Scheduler started.")


async def _post_shutdown(application: Application) -> None:
    scheduler: AsyncIOScheduler | None = application.bot_data.get("scheduler")
    if scheduler:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped.")


def main() -> None:
    if load_dotenv is not None:
        # Load .env next to this file so running from parent folders still works.
        load_dotenv(dotenv_path=Path(__file__).with_name(".env"), encoding="utf-8-sig")
        load_dotenv()

    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token or token == "put_your_token_here":
        raise RuntimeError("Set TELEGRAM_BOT_TOKEN in environment or telegram_notifier_bot/.env file.")

    application = (
        Application.builder()
        .token(token)
        .post_init(_post_init)
        .post_shutdown(_post_shutdown)
        .build()
    )

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("enable_notifications", enable_notifications_command))
    application.add_handler(CommandHandler("disable_notifications", disable_notifications_command))
    application.add_handler(CommandHandler("notifications_status", notifications_status_command))
    application.add_handler(CommandHandler("rules", rules_command))
    application.add_handler(CommandHandler("chat_id", chat_id_command))
    application.add_handler(CommandHandler("sendnow", sendnow_command))

    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
