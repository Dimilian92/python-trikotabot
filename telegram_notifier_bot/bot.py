from __future__ import annotations

import asyncio
import json
import logging
import os
import random
from pathlib import Path

import requests
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

AZTRO_API_URL = "https://api.api-ninjas.com/v1/horoscope"

# Horoscope responses for each sign as fallback (varied by day)
HOROSCOPES = {
    "sagittarius": [
        "Adventure calls! Whether it's exploring something new or taking a risk, the universe supports your bravery. Don't play it safe today. Be the hero of your story! 🚀",
        "Today brings exciting opportunities! Your adventurous spirit is activated. Trust your instincts and don't hesitate to take that leap of faith. Fortune favors the bold!",
        "The stars align in your favor today! Creative energy flows through you. Perfect time to share your ideas and expand your horizons. Be bold, be brilliant! 🎯",
        "Your optimism is contagious today! People are drawn to your energy and enthusiasm. This is your moment to inspire and lead. Seize the day! 🌟",
        "Today's energy encourages growth and expansion. New connections and collaborations are highly favored. Say yes to invitations and new experiences. Great things await! 💫",
        "Your intuition is super sharp today! Trust those gut feelings and follow your instincts. The universe is guiding you toward success. Stay open and receptive! 🎪",
        "Positive vibes surround you! Your natural charisma is amplified. This is the perfect day to pursue your goals and connect with others. You've got this, archer! 🏹✨",
    ],
    "taurus": [
        "Stability and abundance are highlighted today! Your grounded energy attracts good fortune. Focus on what truly matters and trust in your steady progress. Well-deserved success is coming! 💚",
        "Today brings comfort and security. Your practical approach pays off beautifully. Take time to appreciate the good things around you. Gratitude multiplies blessings! 🌾",
        "Your strength and determination shine today! Goals that seemed distant are now within reach. Stay focused and persistent. Your efforts will be rewarded! 💪✨",
        "Financial and personal growth are favored today. Your solid foundation supports new opportunities. Don't be afraid to invest in yourself. The returns will be worth it! 💎",
        "Beauty and harmony surround you today! Your calm, nurturing energy creates positive space around you. Embrace self-care and enjoy life's simple pleasures. You deserve it! 🌸",
        "Your reliability makes you shine today! People trust and depend on you for good reason. This is your time to lead with confidence and integrity. You're a natural! 👑",
        "Blessings flow your way! Your patient, steadfast nature attracts positive energy. Keep moving forward with purpose. Success follows those who stay true to their path! 🌟💚",
    ],
}


def _fetch_horoscope(sign: str) -> str:
    """Fetch horoscope from API Ninjas for the given zodiac sign."""
    try:
        sign_lower = sign.lower()
        response = requests.get(
            AZTRO_API_URL,
            params={"zodiac": sign_lower},
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        horoscope = data.get("horoscope", "")
        if horoscope:
            logger.info("Successfully fetched horoscope for %s", sign)
            return f"🔮 {sign.capitalize()} Daily Horoscope 🔮\n{horoscope}"
        else:
            logger.warning("Empty horoscope text for %s. Response: %s", sign, data)
    except requests.Timeout:
        logger.warning("Timeout fetching horoscope for sign %s", sign)
    except requests.RequestException as e:
        logger.warning("RequestException fetching horoscope for sign %s: %s", sign, e)
    except Exception as e:
        logger.exception("Unexpected error fetching horoscope for sign %s: %s", sign, e)

    # Fallback to random horoscope from curated list
    logger.info("Using fallback horoscope for %s", sign)
    if sign_lower in HOROSCOPES:
        horoscope = random.choice(HOROSCOPES[sign_lower])
        return f"🔮 {sign.capitalize()} Daily Horoscope 🔮\n{horoscope}"
    
    return f"🔮 {sign.capitalize()} Daily Horoscope 🔮\nThe stars are aligned in your favor today!"


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

    days = "disabled" if rule.days is None else ",".join(rule.days)
    times = "disabled" if rule.times is None else ",".join(rule.times)

    if rule.horoscope_sign:
        source = f"API horoscope ({rule.horoscope_sign.capitalize()})"
    else:
        variants = len(rule.messages)
        source = f"{variants} variants | e.g. {rule.messages[0]}"

    return f"{rule.name}: {mentions} | {days} | {times} | {source}"


def _format_notification_text(rule: NotificationRule) -> str:
    mentions = " ".join(rule.mentions).strip()
    message = random.choice(rule.messages)
    if mentions:
        return f"{mentions}\n{message}"
    return message


def _format_notification_text_async(rule: NotificationRule) -> str:
    """Format notification text, fetching from API if needed for horoscope rules."""
    mentions = " ".join(rule.mentions).strip()
    
    if rule.horoscope_sign:
        message = _fetch_horoscope(rule.horoscope_sign)
    else:
        message = random.choice(rule.messages)
    
    if mentions:
        return f"{mentions}\n{message}"
    return message


async def _send_rule_to_chat(application: Application, chat_id: int, rule: NotificationRule) -> None:
    text = _format_notification_text_async(rule)
    await application.bot.send_message(
        chat_id=chat_id,
        text=text,
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

    # Skip message variant check for API-based horoscope rules
    if not rule.horoscope_sign and len(rule.messages) < 7:
        raise ValueError(
            f"Rule {rule.name} must define at least 7 message variants."
        )

    for message in rule.messages:
        if not message.strip():
            raise ValueError(
                f"Rule {rule.name} includes an empty message variant."
            )

    # Disabled rule -> do not validate schedule
    if rule.days is None or rule.times is None:
        logger.info("Rule %s is disabled", rule.name)
        return

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

        if rule.days is None or rule.times is None:
            logger.info("Skipping disabled rule %s", rule.name)
            continue

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

                logger.info(
                    "Scheduled %s on %s at %s (%s)",
                    rule.name,
                    day,
                    clock,
                    BOT_TIMEZONE,
                )


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
