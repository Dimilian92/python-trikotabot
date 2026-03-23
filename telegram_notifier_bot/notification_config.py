from __future__ import annotations

from dataclasses import dataclass


BOT_TIMEZONE = "Europe/Berlin"

WEEKDAYS = ("mon", "tue", "wed", "thu", "fri")


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
        message="Please check in, my love",
        days=WEEKDAYS,
        times=("09:10",),
    ),
    NotificationRule(
        name="lyda_check_out",
        mentions=("@LidiyaBabyak",),
        message="Please check out, and have a great evening!",
        days=WEEKDAYS,
        times=("18:00",),
    ),
    NotificationRule(
        name="vio_collagen",
        mentions=("@vi_vi_es",),
        message="Please drink colagen hahha",
        days=WEEKDAYS,
        times=("11:00",),
    ),
    NotificationRule(
        name="vio_walk",
        mentions=("@vi_vi_es",),
        message="time to drop all and walk. You deserve some yourself time, babe!",
        days=WEEKDAYS,
        times=("18:00",),
    ),
   
)
