from __future__ import annotations

from dataclasses import dataclass


BOT_TIMEZONE = "Europe/Berlin"

WEEKDAYS = ("mon", "tue", "wed", "thu", "fri")
ALL_DAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


@dataclass(frozen=True, slots=True)
class NotificationRule:
    name: str
    mentions: tuple[str, ...]
    message: str
    days: tuple[str, ...]
    times: tuple[str, ...]


NOTIFICATION_RULES: tuple[NotificationRule, ...] = (
    NotificationRule(
        name="lyda_check_in",
        mentions=("@LidiyaBabyak",),
        message="🕘 Check-in time, my love! Clock in before the coffee gets lonely ☕",
        days=WEEKDAYS,
        times=("09:10",),
    ),
    NotificationRule(
        name="lyda_lunch_in",
        mentions=("@LidiyaBabyak",),
        message="🍽️ Lunch o'clock! Time to check out and feed the legend inside you 😄",
        days=WEEKDAYS,
        times=("12:00",),
    ),
    NotificationRule(
        name="lyda_lunch_out",
        mentions=("@LidiyaBabyak",),
        message="⏰ Break over, superstar! Time to check in and pretend we missed work 😅",
        days=WEEKDAYS,
        times=("13:10",),
    ),
    NotificationRule(
        name="lyda_check_out",
        mentions=("@LidiyaBabyak",),
        message="🌇 Check-out time! Great job today, now enjoy your evening like a champion ✨",
        days=WEEKDAYS,
        times=("18:00",),
    ),
    NotificationRule(
        name="vio_collagen",
        mentions=("@vi_vi_es",),
        message="🥤 Collagen o'clock! Sip it now for future-you's glow-up 😎",
        days=WEEKDAYS,
        times=("11:00",),
    ),
    NotificationRule(
        name="lyda_collagen",
        mentions=("@LidiyaBabyak",),
        message="🥤 Collagen reminder: one quick sip now, one happy future selfie later 📸",
        days=WEEKDAYS,
        times=("11:01",),
    ),
    NotificationRule(
        name="vio_walk",
        mentions=("@vi_vi_es",),
        message="🚶 Walk break alert! Drop everything (except your phone), stretch those legs, and claim your me-time 💪",
        days=WEEKDAYS,
        times=("18:00",),
    ),
    NotificationRule(
        name="cat_of_the_day",
        mentions=(),
        message="🐱 Cat of the day nomination",
        days=ALL_DAYS,
        times=("10:00",),
    ),
)
